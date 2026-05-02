from django.db import models
from apps.core.models import TimeStampedModel
from apps.service_orders.models import ServiceOrder


class AIDiagnosticRequest(TimeStampedModel):
    service_order = models.ForeignKey(
        ServiceOrder,
        on_delete=models.CASCADE,
        related_name='ai_diagnostics',
        verbose_name='Orden de servicio',
    )
    prompt = models.TextField(verbose_name='Consulta enviada')
    response = models.TextField(blank=True, verbose_name='Respuesta de la IA')
    model_used = models.CharField(max_length=60, default='gemini-1.5-flash', verbose_name='Modelo usado')
    tokens_used = models.PositiveIntegerField(null=True, blank=True, verbose_name='Tokens utilizados')

    class Meta:
        verbose_name = 'Diagnóstico IA'
        verbose_name_plural = 'Diagnósticos IA'
        ordering = ['-created_at']

    def __str__(self):
        return f'Diagnóstico IA para OS-{self.service_order_id:04d} ({self.created_at:%d/%m/%Y})'
