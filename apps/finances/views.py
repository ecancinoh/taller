from decimal import Decimal
from django.utils import timezone
from django.views.generic import TemplateView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Sum

from apps.core.mixins import MechanicRequiredMixin
from apps.service_orders.models import ServiceOrderPart, ServiceOrderLabor, ServiceOrder
from .models import Expense
from .forms import ExpenseForm


class FinancialDashboardView(MechanicRequiredMixin, TemplateView):
    template_name = 'finances/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = timezone.localdate()

        try:
            month = int(self.request.GET.get('month', today.month))
            year = int(self.request.GET.get('year', today.year))
            # Validar rango
            if month < 1 or month > 12:
                month = today.month
            if year < 2000 or year > 2100:
                year = today.year
        except (ValueError, TypeError):
            month = today.month
            year = today.year

        # Partes del mes
        parts_qs = ServiceOrderPart.objects.filter(
            service_order__service_date__month=month,
            service_order__service_date__year=year,
        )
        # unit_price/unit_cost son por unidad; usamos las properties subtotal y cost_total
        ingresos_repuestos = Decimal('0')
        costos_repuestos = Decimal('0')
        for part in parts_qs.select_related('service_order'):
            ingresos_repuestos += part.subtotal
            costos_repuestos += part.cost_total

        # Mano de obra del mes
        labor_qs = ServiceOrderLabor.objects.filter(
            service_order__service_date__month=month,
            service_order__service_date__year=year,
        )
        ingresos_mano_obra = Decimal('0')
        costos_mano_obra = Decimal('0')
        for labor in labor_qs.select_related('service_order'):
            ingresos_mano_obra += labor.subtotal
            costos_mano_obra += labor.cost_total

        # Gastos adicionales del mes
        gastos_qs = Expense.objects.filter(
            date__month=month,
            date__year=year,
        ).select_related('registered_by')
        total_gastos = gastos_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')

        # Órdenes con actividad en el mes
        ordenes_mes = ServiceOrder.objects.filter(
            service_date__month=month,
            service_date__year=year,
        ).select_related('vehicle', 'vehicle__customer', 'mechanic').order_by('-service_date')

        # Totales
        ingreso_total = ingresos_repuestos + ingresos_mano_obra
        costo_total = costos_repuestos + costos_mano_obra + total_gastos
        ganancia_bruta = ingreso_total - costos_repuestos - costos_mano_obra
        ganancia_neta = ganancia_bruta - total_gastos

        # Construir lista de meses y años para el selector
        meses = [
            (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'),
            (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
            (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre'),
        ]
        years = list(range(today.year - 3, today.year + 2))

        ctx.update({
            'month': month,
            'year': year,
            'meses': meses,
            'years': years,
            'ingresos_repuestos': ingresos_repuestos,
            'costos_repuestos': costos_repuestos,
            'ingresos_mano_obra': ingresos_mano_obra,
            'costos_mano_obra': costos_mano_obra,
            'ingreso_total': ingreso_total,
            'costo_total': costo_total,
            'ganancia_bruta': ganancia_bruta,
            'total_gastos': total_gastos,
            'ganancia_neta': ganancia_neta,
            'ordenes_mes': ordenes_mes,
            'gastos_mes': gastos_qs,
        })
        return ctx


class ExpenseCreateView(MechanicRequiredMixin, CreateView):
    model = Expense
    form_class = ExpenseForm
    template_name = 'finances/expense_form.html'
    success_url = reverse_lazy('finances:dashboard')

    def get_initial(self):
        return {'date': timezone.localdate()}

    def form_valid(self, form):
        form.instance.registered_by = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = 'Nuevo gasto'
        ctx['btn_texto'] = 'Guardar gasto'
        return ctx


class ExpenseUpdateView(MechanicRequiredMixin, UpdateView):
    model = Expense
    form_class = ExpenseForm
    template_name = 'finances/expense_form.html'
    success_url = reverse_lazy('finances:dashboard')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = 'Editar gasto'
        ctx['btn_texto'] = 'Guardar cambios'
        return ctx


class ExpenseDeleteView(MechanicRequiredMixin, DeleteView):
    model = Expense
    template_name = 'finances/expense_confirm_delete.html'
    success_url = reverse_lazy('finances:dashboard')
