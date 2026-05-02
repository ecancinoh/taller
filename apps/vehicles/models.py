from django.db import models
from apps.core.models import TimeStampedModel
from apps.customers.models import Customer


class Vehicle(TimeStampedModel):
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name='vehicles',
        verbose_name='Cliente',
    )
    brand = models.CharField(max_length=60, verbose_name='Marca')
    model = models.CharField(max_length=60, verbose_name='Modelo')
    year = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name='Año')
    license_plate = models.CharField(max_length=20, blank=True, verbose_name='Patente')
    vin = models.CharField(max_length=17, blank=True, verbose_name='Número de serie (VIN)')
    color = models.CharField(max_length=40, blank=True, verbose_name='Color')
    engine = models.CharField(max_length=60, blank=True, verbose_name='Motor')
    notes = models.TextField(blank=True, verbose_name='Notas')

    class Meta:
        verbose_name = 'Vehículo'
        verbose_name_plural = 'Vehículos'
        ordering = ['brand', 'model']

    def __str__(self):
        parts = [self.brand, self.model]
        if self.year:
            parts.append(str(self.year))
        if self.license_plate:
            parts.append(f'[{self.license_plate}]')
        return ' '.join(parts)
