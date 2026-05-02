from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.contrib import messages
from apps.core.mixins import MechanicRequiredMixin
from .models import Vehicle
from .forms import VehicleForm


class VehicleListView(MechanicRequiredMixin, ListView):
    model = Vehicle
    template_name = 'vehicles/vehicle_list.html'
    context_object_name = 'vehicles'
    paginate_by = 20

    def get_queryset(self):
        qs = Vehicle.objects.select_related('customer')
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = (
                qs.filter(brand__icontains=q) |
                qs.filter(model__icontains=q) |
                qs.filter(license_plate__icontains=q) |
                qs.filter(customer__first_name__icontains=q) |
                qs.filter(customer__last_name__icontains=q)
            )
        return qs.order_by('brand', 'model')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        return ctx


class VehicleDetailView(MechanicRequiredMixin, DetailView):
    model = Vehicle
    template_name = 'vehicles/vehicle_detail.html'
    context_object_name = 'vehicle'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['service_orders'] = (
            self.object.service_orders
            .select_related('mechanic')
            .order_by('-service_date')
        )
        return ctx


class VehicleCreateView(MechanicRequiredMixin, CreateView):
    model = Vehicle
    form_class = VehicleForm
    template_name = 'vehicles/vehicle_form.html'
    success_url = reverse_lazy('vehicles:list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['customer_id'] = self.request.GET.get('customer')
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Vehículo registrado correctamente.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Registrar vehículo'
        ctx['btn_text'] = 'Guardar vehículo'
        return ctx


class VehicleUpdateView(MechanicRequiredMixin, UpdateView):
    model = Vehicle
    form_class = VehicleForm
    template_name = 'vehicles/vehicle_form.html'

    def get_success_url(self):
        return reverse_lazy('vehicles:detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, 'Vehículo actualizado correctamente.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Editar: {self.object}'
        ctx['btn_text'] = 'Guardar cambios'
        return ctx

