from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.contrib import messages
from apps.core.mixins import MechanicRequiredMixin
from .models import Customer
from .forms import CustomerForm


class CustomerListView(MechanicRequiredMixin, ListView):
    model = Customer
    template_name = 'customers/customer_list.html'
    context_object_name = 'customers'
    paginate_by = 20

    def get_queryset(self):
        qs = Customer.objects.select_related('created_by')
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                first_name__icontains=q
            ) | qs.filter(
                last_name__icontains=q
            ) | qs.filter(
                phone__icontains=q
            )
        return qs.order_by('last_name', 'first_name')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        return ctx


class CustomerDetailView(MechanicRequiredMixin, DetailView):
    model = Customer
    template_name = 'customers/customer_detail.html'
    context_object_name = 'customer'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['vehicles'] = self.object.vehicles.all()
        ctx['recent_orders'] = (
            self.object.vehicles
            .values_list('service_orders', flat=True)
        )
        return ctx


class CustomerCreateView(MechanicRequiredMixin, CreateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'customers/customer_form.html'
    success_url = reverse_lazy('customers:list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Cliente creado correctamente.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Nuevo cliente'
        ctx['btn_text'] = 'Guardar cliente'
        return ctx


class CustomerUpdateView(MechanicRequiredMixin, UpdateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'customers/customer_form.html'
    success_url = reverse_lazy('customers:list')

    def form_valid(self, form):
        messages.success(self.request, 'Cliente actualizado correctamente.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Editar: {self.object.full_name}'
        ctx['btn_text'] = 'Guardar cambios'
        return ctx

