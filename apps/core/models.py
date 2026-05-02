from django.db import models


class TimeStampedModel(models.Model):
    """Modelo abstracto base con fechas de creación y actualización."""
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Creado el')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Actualizado el')

    class Meta:
        abstract = True
