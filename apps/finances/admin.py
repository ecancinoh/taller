from django.contrib import admin
from .models import Expense


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('category', 'description', 'amount', 'date', 'registered_by', 'created_at')
    list_filter = ('category', 'date')
    search_fields = ('category', 'description')
    date_hierarchy = 'date'
