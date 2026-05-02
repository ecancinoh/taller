from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.contrib import messages
from apps.core.mixins import MechanicRequiredMixin, AdminRequiredMixin
from .models import ServiceOrder
from .forms import ServiceOrderForm


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
        ctx['show_financials'] = self.request.user.is_admin
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
        ctx['title'] = f'Editar OS-{self.object.pk:04d}'
        ctx['btn_text'] = 'Guardar cambios'
        return ctx

