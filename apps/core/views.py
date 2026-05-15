import re

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.utils import timezone
from django.views.generic import TemplateView
from apps.customers.models import Customer
from apps.vehicles.models import Vehicle
from apps.service_orders.models import ServiceOrder


def _sum_order_totals(orders):
    return sum(order.grand_total for order in orders)


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
        today = timezone.localdate()
        month_orders = ServiceOrder.objects.filter(
            service_date__year=today.year,
            service_date__month=today.month,
        ).prefetch_related('parts', 'labors')

        if user.is_admin:
            all_orders = ServiceOrder.objects.select_related('vehicle__customer', 'mechanic')
            ctx['total_customers'] = Customer.objects.count()
            ctx['total_vehicles'] = Vehicle.objects.count()
            ctx['active_orders'] = all_orders.filter(status__in=active_statuses).count()
            ctx['total_orders'] = all_orders.count()
            ctx['pending_orders'] = all_orders.filter(status=ServiceOrder.Status.PENDING).count()
            ctx['in_progress_orders'] = all_orders.filter(status=ServiceOrder.Status.IN_PROGRESS).count()
            ctx['waiting_parts_orders'] = all_orders.filter(status=ServiceOrder.Status.WAITING_PARTS).count()
            ctx['ready_orders'] = all_orders.filter(status=ServiceOrder.Status.DONE).count()
            ctx['month_income'] = _sum_order_totals(month_orders)
            ctx['today_orders'] = all_orders.filter(service_date=today).count()
            ctx['recent_orders'] = (
                all_orders
                .order_by('-created_at')[:8]
            )
        else:
            my_orders = ServiceOrder.objects.filter(mechanic=user).select_related('vehicle__customer')
            my_month_orders = month_orders.filter(mechanic=user)
            # Mecánico: solo sus órdenes
            ctx['my_active_orders'] = (
                my_orders
                .filter(status__in=active_statuses)
                .order_by('-service_date')
            )
            ctx['my_pending_orders'] = my_orders.filter(status=ServiceOrder.Status.PENDING).count()
            ctx['my_in_progress_orders'] = my_orders.filter(status=ServiceOrder.Status.IN_PROGRESS).count()
            ctx['my_waiting_parts_orders'] = my_orders.filter(status=ServiceOrder.Status.WAITING_PARTS).count()
            ctx['my_ready_orders'] = my_orders.filter(status=ServiceOrder.Status.DONE).count()
            ctx['my_today_orders'] = my_orders.filter(service_date=today).count()
            ctx['my_month_income'] = _sum_order_totals(my_month_orders)
            ctx['my_done_today'] = (
                my_orders
                .filter(status=ServiceOrder.Status.DONE)
                .order_by('-updated_at')[:5]
            )

        return ctx


class GlobalSearchView(LoginRequiredMixin, TemplateView):
    template_name = 'core/search_results.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        query = self.request.GET.get('q', '').strip()
        normalized_order = re.sub(r'[^0-9]', '', query)
        order_number = int(normalized_order) if normalized_order.isdigit() else None

        customer_results = Customer.objects.none()
        vehicle_results = Vehicle.objects.none()
        order_results = ServiceOrder.objects.none()

        if query:
            customer_results = (
                Customer.objects.filter(
                    Q(first_name__icontains=query)
                    | Q(last_name__icontains=query)
                    | Q(phone__icontains=query)
                )
                .order_by('last_name', 'first_name')[:8]
            )

            vehicle_results = (
                Vehicle.objects.select_related('customer')
                .filter(
                    Q(brand__icontains=query)
                    | Q(model__icontains=query)
                    | Q(license_plate__icontains=query)
                    | Q(customer__first_name__icontains=query)
                    | Q(customer__last_name__icontains=query)
                    | Q(customer__phone__icontains=query)
                )
                .order_by('brand', 'model')[:8]
            )

            order_query = (
                Q(vehicle__license_plate__icontains=query)
                | Q(vehicle__customer__first_name__icontains=query)
                | Q(vehicle__customer__last_name__icontains=query)
                | Q(vehicle__customer__phone__icontains=query)
            )
            if order_number is not None:
                order_query |= Q(pk=order_number)

            order_results = ServiceOrder.objects.select_related('vehicle__customer', 'mechanic').filter(order_query)
            if not self.request.user.is_admin:
                order_results = order_results.filter(mechanic=self.request.user)
            order_results = order_results.order_by('-service_date', '-created_at')[:8]

        ctx.update({
            'q': query,
            'customer_results': customer_results,
            'vehicle_results': vehicle_results,
            'order_results': order_results,
            'result_count': customer_results.count() + vehicle_results.count() + order_results.count(),
        })
        return ctx

