from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from apps.customers.models import Customer
from apps.vehicles.models import Vehicle
from apps.service_orders.models import ServiceOrder


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'core/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user

        active_statuses = [
            ServiceOrder.Status.PENDING,
            ServiceOrder.Status.IN_PROGRESS,
            ServiceOrder.Status.WAITING_PARTS,
        ]

        if user.is_admin:
            ctx['total_customers'] = Customer.objects.count()
            ctx['total_vehicles'] = Vehicle.objects.count()
            ctx['active_orders'] = ServiceOrder.objects.filter(status__in=active_statuses).count()
            ctx['total_orders'] = ServiceOrder.objects.count()
            ctx['recent_orders'] = (
                ServiceOrder.objects
                .select_related('vehicle__customer', 'mechanic')
                .order_by('-created_at')[:8]
            )
        else:
            # Mecánico: solo sus órdenes
            ctx['my_active_orders'] = (
                ServiceOrder.objects
                .filter(mechanic=user, status__in=active_statuses)
                .select_related('vehicle__customer')
                .order_by('-service_date')
            )
            ctx['my_done_today'] = (
                ServiceOrder.objects
                .filter(mechanic=user, status=ServiceOrder.Status.DONE)
                .select_related('vehicle__customer')
                .order_by('-updated_at')[:5]
            )

        return ctx

