from django.db import models
from apps.core.models import TimeStampedModel


class Expense(TimeStampedModel):
    """Gasto adicional del taller (arriendo, herramientas, servicios, etc.)."""

    category = models.CharField(max_length=100, verbose_name='Categoría')
    description = models.CharField(max_length=255, verbose_name='Descripción')
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Monto')
    date = models.DateField(verbose_name='Fecha')
    registered_by = models.ForeignKey(
        'accounts.CustomUser',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name='Registrado por',
        related_name='expenses',
    )

    class Meta:
        verbose_name = 'Gasto'
        verbose_name_plural = 'Gastos'
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f'{self.category} — ${self.amount} ({self.date})'
