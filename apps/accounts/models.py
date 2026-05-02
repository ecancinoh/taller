from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Administrador'
        MECHANIC = 'MECHANIC', 'Mecánico'

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.MECHANIC,
        verbose_name='Rol',
    )
    phone = models.CharField(max_length=20, blank=True, verbose_name='Teléfono')

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def save(self, *args, **kwargs):
        # Garantiza consistencia: cualquier superusuario debe tener rol ADMIN.
        if self.is_superuser:
            self.role = self.Role.ADMIN
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.get_full_name() or self.username} ({self.get_role_display()})'

    @property
    def is_admin(self):
        return self.is_superuser or self.role == self.Role.ADMIN

    @property
    def is_mechanic(self):
        return (not self.is_superuser) and self.role == self.Role.MECHANIC
