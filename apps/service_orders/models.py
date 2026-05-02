import uuid
from django.db import models
from django.conf import settings
from apps.core.models import TimeStampedModel
from apps.vehicles.models import Vehicle


class ServiceOrder(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pendiente'
        IN_PROGRESS = 'IN_PROGRESS', 'En progreso'
        WAITING_PARTS = 'WAITING_PARTS', 'Esperando repuestos'
        DONE = 'DONE', 'Terminada'
        DELIVERED = 'DELIVERED', 'Entregada'
        CANCELLED = 'CANCELLED', 'Cancelada'

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.PROTECT,
        related_name='service_orders',
        verbose_name='Vehículo',
    )
    mechanic = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='service_orders',
        verbose_name='Mecánico',
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name='Estado',
    )
    service_date = models.DateField(verbose_name='Fecha de servicio')
    mileage = models.PositiveIntegerField(null=True, blank=True, verbose_name='Kilometraje')

    # Campos del cliente
    customer_complaint = models.TextField(verbose_name='Motivo reportado por cliente')

    # Campos del mecánico
    mechanic_observations = models.TextField(blank=True, verbose_name='Observaciones del mecánico')
    diagnosis = models.TextField(blank=True, verbose_name='Diagnóstico')
    work_done = models.TextField(blank=True, verbose_name='Trabajo realizado')
    recommendations = models.TextField(blank=True, verbose_name='Recomendaciones')

    # Solo visible para Admin
    internal_notes = models.TextField(blank=True, verbose_name='Notas internas')

    class Meta:
        verbose_name = 'Orden de servicio'
        verbose_name_plural = 'Órdenes de servicio'
        ordering = ['-service_date', '-created_at']

    def __str__(self):
        return f'OS-{self.pk:04d} | {self.vehicle} | {self.get_status_display()}'

    @property
    def customer(self):
        return self.vehicle.customer

    @property
    def total_parts(self):
        return sum(p.subtotal for p in self.parts.all())

    @property
    def total_labor(self):
        return sum(l.subtotal for l in self.labors.all())

    @property
    def grand_total(self):
        return self.total_parts + self.total_labor


class ServiceOrderPart(TimeStampedModel):
    service_order = models.ForeignKey(
        ServiceOrder,
        on_delete=models.CASCADE,
        related_name='parts',
        verbose_name='Orden',
    )
    name = models.CharField(max_length=200, verbose_name='Repuesto')
    quantity = models.DecimalField(max_digits=8, decimal_places=2, default=1, verbose_name='Cantidad')
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Precio unitario')
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Costo unitario')
    notes = models.CharField(max_length=255, blank=True, verbose_name='Notas')

    class Meta:
        verbose_name = 'Repuesto'
        verbose_name_plural = 'Repuestos'

    def __str__(self):
        return f'{self.name} x{self.quantity}'

    @property
    def subtotal(self):
        return self.quantity * self.unit_price

    @property
    def cost_total(self):
        return self.quantity * self.unit_cost


class ServiceOrderLabor(TimeStampedModel):
    service_order = models.ForeignKey(
        ServiceOrder,
        on_delete=models.CASCADE,
        related_name='labors',
        verbose_name='Orden',
    )
    description = models.CharField(max_length=200, verbose_name='Descripción')
    hours = models.DecimalField(max_digits=6, decimal_places=2, default=1, verbose_name='Horas')
    price_per_hour = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Precio por hora')
    cost_per_hour = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Costo por hora')

    class Meta:
        verbose_name = 'Mano de obra'
        verbose_name_plural = 'Mano de obra'

    def __str__(self):
        return self.description

    @property
    def subtotal(self):
        return self.hours * self.price_per_hour

    @property
    def cost_total(self):
        return self.hours * self.cost_per_hour


class ServiceOrderPhoto(TimeStampedModel):
    service_order = models.ForeignKey(
        ServiceOrder,
        on_delete=models.CASCADE,
        related_name='photos',
        verbose_name='Orden',
    )
    image = models.ImageField(upload_to='service_orders/%Y/%m/', verbose_name='Imagen')
    caption = models.CharField(max_length=200, blank=True, verbose_name='Descripción')
    is_public = models.BooleanField(default=True, verbose_name='Visible en vista pública')
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Subida por',
    )

    class Meta:
        verbose_name = 'Foto'
        verbose_name_plural = 'Fotos'

    def __str__(self):
        return self.caption or f'Foto #{self.pk}'


class ShareToken(TimeStampedModel):
    service_order = models.OneToOneField(
        ServiceOrder,
        on_delete=models.CASCADE,
        related_name='share_token',
        verbose_name='Orden',
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    is_active = models.BooleanField(default=True, verbose_name='Activo')
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name='Expira el')

    class Meta:
        verbose_name = 'Token compartido'
        verbose_name_plural = 'Tokens compartidos'

    def __str__(self):
        return f'Token para OS-{self.service_order_id:04d}'
