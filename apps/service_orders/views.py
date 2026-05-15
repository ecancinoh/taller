from urllib.parse import quote

from django import forms as django_forms
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.utils import timezone
from apps.core.mixins import MechanicRequiredMixin
from apps.customers.models import Customer
from apps.customers.forms import CustomerForm
from apps.vehicles.models import Vehicle
from apps.vehicles.forms import VehicleForm
from .models import ServiceOrder, ServiceOrderPart, ServiceOrderLabor, ShareToken
from .forms import ServiceOrderForm, ServiceOrderPartForm, ServiceOrderLaborForm, ServiceOrderPhotoForm


class ServiceOrderListView(MechanicRequiredMixin, ListView):
    model = ServiceOrder
    template_name = 'service_orders/order_list.html'
    context_object_name = 'orders'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        qs = ServiceOrder.objects.select_related('vehicle__customer', 'mechanic')
        if not user.is_admin:
            qs = qs.filter(mechanic=user)
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        q = self.request.GET.get('q', '').strip()
        if q:
            normalized_order = ''.join(ch for ch in q if ch.isdigit())
            order_query = Q()
            if normalized_order:
                order_query |= Q(pk=int(normalized_order))
            qs = (
                qs.filter(
                    order_query
                    | Q(vehicle__license_plate__icontains=q)
                    | Q(vehicle__brand__icontains=q)
                    | Q(vehicle__customer__first_name__icontains=q)
                    | Q(vehicle__customer__last_name__icontains=q)
                    | Q(vehicle__customer__phone__icontains=q)
                )
            )
        return qs.order_by('-service_date', '-created_at')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['status_choices'] = ServiceOrder.Status.choices
        ctx['current_status'] = self.request.GET.get('status', '')
        ctx['q'] = self.request.GET.get('q', '')
        return ctx


class ServiceOrderDetailView(MechanicRequiredMixin, DetailView):
    model = ServiceOrder
    template_name = 'service_orders/order_detail.html'
    context_object_name = 'order'

    def get_queryset(self):
        qs = super().get_queryset().select_related('vehicle__customer', 'mechanic')
        if not self.request.user.is_admin:
            qs = qs.filter(mechanic=self.request.user)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['parts'] = self.object.parts.all()
        ctx['labors'] = self.object.labors.all()
        ctx['photos'] = self.object.photos.all()
        ctx['last_diagnostic'] = self.object.ai_diagnostics.order_by('-created_at').first()
        ctx['photo_form'] = ServiceOrderPhotoForm()
        ctx['part_form'] = ServiceOrderPartForm()
        ctx['labor_form'] = ServiceOrderLaborForm()
        ctx['show_financials'] = self.request.user.is_admin
        ctx['show_internal_notes'] = self.request.user.is_admin

        share_token = getattr(self.object, 'share_token', None)
        is_share_link_active = (
            share_token
            and share_token.is_active
            and (share_token.expires_at is None or share_token.expires_at > timezone.now())
        )
        if is_share_link_active:
            public_path = reverse('shared_views:public_order', kwargs={'token': share_token.token})
            share_url = self.request.build_absolute_uri(public_path)
            ctx['share_url'] = share_url

            customer_phone = (self.object.customer.phone or '').strip()
            normalized_phone = ''.join(ch for ch in customer_phone if ch.isdigit() or ch == '+')
            if normalized_phone:
                wa_message = quote(
                    f'Hola, te compartimos el detalle de tu orden de servicio ({self.object.vehicle}). '
                    f'Revisa aquí: {share_url}'
                )
                ctx['whatsapp_share_url'] = f'https://wa.me/{normalized_phone.lstrip("+")}?text={wa_message}'

        return ctx


class ServiceOrderCreateView(MechanicRequiredMixin, CreateView):
    model = ServiceOrder
    form_class = ServiceOrderForm
    template_name = 'service_orders/order_form.html'

    def _panel_is_open(self, name):
        return self.request.POST.get(name) == '1'

    def _resolve_selected_entities(self, customer_id=None, vehicle_id=None):
        selected_customer = None
        selected_vehicle = None

        if vehicle_id:
            try:
                selected_vehicle = Vehicle.objects.select_related('customer').get(pk=vehicle_id)
                selected_customer = selected_vehicle.customer
            except (Vehicle.DoesNotExist, ValueError, TypeError):
                selected_vehicle = None

        if customer_id and not selected_customer:
            try:
                selected_customer = Customer.objects.get(pk=customer_id)
            except (Customer.DoesNotExist, ValueError, TypeError):
                selected_customer = None

        return selected_customer, selected_vehicle

    def _build_order_form(self, data=None, customer_id=None, vehicle_id=None):
        return self.form_class(
            data=data,
            user=self.request.user,
            customer_id=customer_id,
            vehicle_id=vehicle_id,
        )

    def _build_customer_form(self, data=None):
        return CustomerForm(data=data, prefix='quick_customer')

    def _build_vehicle_form(self, data=None, customer_id=None):
        vehicle_data = data.copy() if data is not None else None
        if vehicle_data is not None and customer_id and not vehicle_data.get('quick_vehicle-customer'):
            vehicle_data['quick_vehicle-customer'] = str(customer_id)

        form = VehicleForm(data=vehicle_data, prefix='quick_vehicle', customer_id=customer_id)
        if customer_id:
            form.fields['customer'].widget = django_forms.HiddenInput()
            form.fields['customer'].initial = customer_id
        return form

    def post(self, request, *args, **kwargs):
        self.object = None
        action = request.POST.get('action', 'create_order')
        current_customer_id = request.POST.get('quick_vehicle-customer') or request.GET.get('customer')
        current_vehicle_id = request.GET.get('vehicle')
        selected_customer, selected_vehicle = self._resolve_selected_entities(current_customer_id, current_vehicle_id)
        open_quick_customer = self._panel_is_open('ui_quick_customer_open')
        open_quick_vehicle = self._panel_is_open('ui_quick_vehicle_open')
        open_advanced_fields = self._panel_is_open('ui_advanced_open')

        if action == 'quick_customer':
            customer_form = self._build_customer_form(request.POST)
            order_form = self._build_order_form(
                data=request.POST,
                customer_id=selected_customer.pk if selected_customer else None,
                vehicle_id=selected_vehicle.pk if selected_vehicle else None,
            )
            if customer_form.is_valid():
                customer = customer_form.save(commit=False)
                customer.created_by = request.user
                customer.save()
                messages.success(request, 'Cliente creado y seleccionado para la orden.')
                return self.render_to_response(
                    self.get_context_data(
                        form=self._build_order_form(data=request.POST, customer_id=customer.pk),
                        customer_form=self._build_customer_form(),
                        vehicle_form=self._build_vehicle_form(customer_id=customer.pk),
                        selected_customer=customer,
                        selected_vehicle=None,
                        open_quick_vehicle=True,
                        open_advanced_fields=open_advanced_fields,
                    )
                )

            return self.render_to_response(
                self.get_context_data(
                    form=order_form,
                    customer_form=customer_form,
                    vehicle_form=self._build_vehicle_form(customer_id=selected_customer.pk if selected_customer else None),
                    selected_customer=selected_customer,
                    selected_vehicle=selected_vehicle,
                    open_quick_customer=True,
                    open_quick_vehicle=open_quick_vehicle,
                    open_advanced_fields=open_advanced_fields,
                )
            )

        if action == 'quick_vehicle':
            vehicle_form = self._build_vehicle_form(request.POST, customer_id=selected_customer.pk if selected_customer else None)
            order_form = self._build_order_form(
                data=request.POST,
                customer_id=selected_customer.pk if selected_customer else None,
                vehicle_id=selected_vehicle.pk if selected_vehicle else None,
            )

            if vehicle_form.is_valid():
                vehicle = vehicle_form.save()
                order_data = request.POST.copy()
                order_data['vehicle'] = str(vehicle.pk)
                messages.success(request, 'Vehículo creado y seleccionado para la orden.')
                return self.render_to_response(
                    self.get_context_data(
                        form=self._build_order_form(data=order_data, customer_id=vehicle.customer_id, vehicle_id=vehicle.pk),
                        customer_form=self._build_customer_form(),
                        vehicle_form=self._build_vehicle_form(customer_id=vehicle.customer_id),
                        selected_customer=vehicle.customer,
                        selected_vehicle=vehicle,
                        open_advanced_fields=open_advanced_fields,
                    )
                )

            return self.render_to_response(
                self.get_context_data(
                    form=order_form,
                    customer_form=self._build_customer_form(),
                    vehicle_form=vehicle_form,
                    selected_customer=selected_customer,
                    selected_vehicle=selected_vehicle,
                    open_quick_vehicle=True,
                    open_quick_customer=open_quick_customer,
                    open_advanced_fields=open_advanced_fields,
                )
            )

        return super().post(request, *args, **kwargs)

    def form_invalid(self, form):
        customer_id = self.request.POST.get('quick_vehicle-customer') or self.request.GET.get('customer')
        vehicle_id = self.request.POST.get('vehicle') or self.request.GET.get('vehicle')
        selected_customer, selected_vehicle = self._resolve_selected_entities(customer_id, vehicle_id)
        return self.render_to_response(
            self.get_context_data(
                form=form,
                customer_form=self._build_customer_form(self.request.POST),
                vehicle_form=self._build_vehicle_form(self.request.POST, customer_id=selected_customer.pk if selected_customer else None),
                selected_customer=selected_customer,
                selected_vehicle=selected_vehicle,
                open_quick_customer=self._panel_is_open('ui_quick_customer_open'),
                open_quick_vehicle=self._panel_is_open('ui_quick_vehicle_open'),
                open_advanced_fields=self._panel_is_open('ui_advanced_open'),
            )
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['customer_id'] = self.request.GET.get('customer')
        kwargs['vehicle_id'] = self.request.GET.get('vehicle')
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Orden de servicio creada correctamente.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('service_orders:detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        customer_id = self.request.GET.get('customer')
        vehicle_id = self.request.GET.get('vehicle')
        selected_customer, selected_vehicle = self._resolve_selected_entities(customer_id, vehicle_id)

        ctx['title'] = 'Nueva orden de servicio'
        ctx['btn_text'] = 'Crear orden'
        ctx['can_upload_photos'] = False
        ctx['selected_customer'] = kwargs.get('selected_customer', selected_customer)
        ctx['selected_vehicle'] = kwargs.get('selected_vehicle', selected_vehicle)
        ctx['customer_form'] = kwargs.get('customer_form', self._build_customer_form())
        ctx['vehicle_form'] = kwargs.get(
            'vehicle_form',
            self._build_vehicle_form(customer_id=ctx['selected_customer'].pk if ctx['selected_customer'] else None),
        )
        ctx['open_quick_customer'] = kwargs.get('open_quick_customer', False)
        ctx['open_quick_vehicle'] = kwargs.get('open_quick_vehicle', False)
        ctx['open_advanced_fields'] = kwargs.get('open_advanced_fields', False)
        return ctx


class ServiceOrderUpdateView(MechanicRequiredMixin, UpdateView):
    model = ServiceOrder
    form_class = ServiceOrderForm
    template_name = 'service_orders/order_form.html'

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_admin:
            qs = qs.filter(mechanic=self.request.user)
        return qs

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Orden actualizada correctamente.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('service_orders:detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['order'] = self.object
        ctx['title'] = f'Editar OS-{self.object.pk:04d}'
        ctx['btn_text'] = 'Guardar cambios'
        ctx['can_upload_photos'] = True
        ctx['photo_form'] = ServiceOrderPhotoForm()
        ctx['photos'] = self.object.photos.all()
        return ctx


class ServiceOrderPhotoUploadView(MechanicRequiredMixin, View):
    def post(self, request, pk):
        qs = ServiceOrder.objects.select_related('mechanic')
        if not request.user.is_admin:
            qs = qs.filter(mechanic=request.user)
        order = get_object_or_404(qs, pk=pk)

        form = ServiceOrderPhotoForm(request.POST, request.FILES)
        if not form.is_valid():
            messages.error(request, 'No se pudo subir la foto. Verifica el archivo y vuelve a intentar.')
            next_url = request.POST.get('next', '').strip()
            if next_url:
                return redirect(next_url)
            return redirect('service_orders:detail', pk=order.pk)

        photo = form.save(commit=False)
        photo.service_order = order
        photo.uploaded_by = request.user
        photo.save()

        messages.success(request, 'Foto subida correctamente.')
        next_url = request.POST.get('next', '').strip()
        if next_url:
            return redirect(next_url)
        return redirect('service_orders:detail', pk=order.pk)


class ServiceOrderShareLinkView(MechanicRequiredMixin, View):
    def post(self, request, pk):
        qs = ServiceOrder.objects.select_related('mechanic')
        if not request.user.is_admin:
            qs = qs.filter(mechanic=request.user)
        order = get_object_or_404(qs, pk=pk)

        share_token, created = ShareToken.objects.get_or_create(service_order=order)
        if not share_token.is_active:
            share_token.is_active = True
            share_token.expires_at = None
            share_token.save(update_fields=['is_active', 'expires_at'])
            created = True

        if created:
            messages.success(request, 'Enlace de cliente generado correctamente.')
        else:
            messages.info(request, 'Ya existía un enlace activo para esta orden.')

        return redirect('service_orders:detail', pk=order.pk)


# ─── Repuestos (Parts) inline CRUD ───────────────────────────────────────────

def _get_order_for_user(user, order_pk):
    """Devuelve la orden si el usuario tiene acceso, lanza 404 si no existe o 403 si no tiene permiso."""
    order = get_object_or_404(ServiceOrder, pk=order_pk)
    if not user.is_admin and order.mechanic != user:
        raise PermissionDenied
    return order


class ServiceOrderPartCreateView(MechanicRequiredMixin, View):
    def post(self, request, pk):
        order = _get_order_for_user(request.user, pk)
        form = ServiceOrderPartForm(request.POST)
        if form.is_valid():
            part = form.save(commit=False)
            part.service_order = order
            part.save()
            messages.success(request, 'Repuesto agregado.')
        else:
            for field_errors in form.errors.values():
                for error in field_errors:
                    messages.error(request, error)
        return redirect('service_orders:detail', pk=pk)


class ServiceOrderPartUpdateView(MechanicRequiredMixin, UpdateView):
    model = ServiceOrderPart
    form_class = ServiceOrderPartForm
    template_name = 'service_orders/part_form.html'

    def get_queryset(self):
        qs = super().get_queryset().select_related('service_order')
        if not self.request.user.is_admin:
            qs = qs.filter(service_order__mechanic=self.request.user)
        return qs

    def get_success_url(self):
        messages.success(self.request, 'Repuesto actualizado.')
        return reverse('service_orders:detail', kwargs={'pk': self.object.service_order_id})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['order'] = self.object.service_order
        ctx['titulo'] = 'Editar repuesto'
        return ctx


class ServiceOrderPartDeleteView(MechanicRequiredMixin, View):
    def post(self, request, pk):
        qs = ServiceOrderPart.objects.select_related('service_order')
        if not request.user.is_admin:
            qs = qs.filter(service_order__mechanic=request.user)
        part = get_object_or_404(qs, pk=pk)
        order_pk = part.service_order_id
        part.delete()
        messages.success(request, 'Repuesto eliminado.')
        return redirect('service_orders:detail', pk=order_pk)


# ─── Mano de obra (Labor) inline CRUD ────────────────────────────────────────

class ServiceOrderLaborCreateView(MechanicRequiredMixin, View):
    def post(self, request, pk):
        order = _get_order_for_user(request.user, pk)
        form = ServiceOrderLaborForm(request.POST)
        if form.is_valid():
            labor = form.save(commit=False)
            labor.service_order = order
            labor.hours = 1
            labor.cost_per_hour = 0
            labor.save()
            messages.success(request, 'Mano de obra agregada.')
        else:
            for field_errors in form.errors.values():
                for error in field_errors:
                    messages.error(request, error)
        return redirect('service_orders:detail', pk=pk)


class ServiceOrderLaborUpdateView(MechanicRequiredMixin, UpdateView):
    model = ServiceOrderLabor
    form_class = ServiceOrderLaborForm
    template_name = 'service_orders/labor_form.html'

    def get_queryset(self):
        qs = super().get_queryset().select_related('service_order')
        if not self.request.user.is_admin:
            qs = qs.filter(service_order__mechanic=self.request.user)
        return qs

    def form_valid(self, form):
        form.instance.hours = 1
        form.instance.cost_per_hour = 0
        messages.success(self.request, 'Mano de obra actualizada.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('service_orders:detail', kwargs={'pk': self.object.service_order_id})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['order'] = self.object.service_order
        ctx['titulo'] = 'Editar mano de obra'
        return ctx


class ServiceOrderLaborDeleteView(MechanicRequiredMixin, View):
    def post(self, request, pk):
        qs = ServiceOrderLabor.objects.select_related('service_order')
        if not request.user.is_admin:
            qs = qs.filter(service_order__mechanic=request.user)
        labor = get_object_or_404(qs, pk=pk)
        order_pk = labor.service_order_id
        labor.delete()
        messages.success(request, 'Mano de obra eliminada.')
        return redirect('service_orders:detail', pk=order_pk)

