from urllib.parse import quote

from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.utils import timezone
from apps.core.mixins import MechanicRequiredMixin
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
            qs = (
                qs.filter(vehicle__license_plate__icontains=q) |
                qs.filter(vehicle__brand__icontains=q) |
                qs.filter(vehicle__customer__first_name__icontains=q) |
                qs.filter(vehicle__customer__last_name__icontains=q)
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
        ctx['show_financials'] = True  # Mecánicos y admins ven datos financieros
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

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Orden de servicio creada correctamente.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('service_orders:detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Nueva orden de servicio'
        ctx['btn_text'] = 'Crear orden'
        ctx['can_upload_photos'] = False
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

