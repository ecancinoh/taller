from django.contrib import admin
from .models import Vehicle

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'customer', 'license_plate', 'year']
    list_select_related = ['customer']
    search_fields = ['brand', 'model', 'license_plate', 'vin']
