from django.contrib import admin
from .models import ServiceOrder, ServiceOrderPart, ServiceOrderLabor, ServiceOrderPhoto, ShareToken

class PartInline(admin.TabularInline):
    model = ServiceOrderPart
    extra = 0

class LaborInline(admin.TabularInline):
    model = ServiceOrderLabor
    extra = 0

@admin.register(ServiceOrder)
class ServiceOrderAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'vehicle', 'mechanic', 'status', 'service_date']
    list_filter = ['status', 'service_date']
    search_fields = ['vehicle__brand', 'vehicle__license_plate', 'vehicle__customer__first_name']
    inlines = [PartInline, LaborInline]
    list_select_related = ['vehicle__customer', 'mechanic']

@admin.register(ShareToken)
class ShareTokenAdmin(admin.ModelAdmin):
    list_display = ['service_order', 'token', 'is_active', 'created_at']
    readonly_fields = ['token']
