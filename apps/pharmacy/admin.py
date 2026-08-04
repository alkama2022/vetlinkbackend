from django.contrib import admin
from .models import DrugStock

@admin.register(DrugStock)
class DrugStockAdmin(admin.ModelAdmin):
    list_display = ('drug_code', 'name', 'category', 'quantity', 'unit', 'reorder_level', 'expiry_date', 'unit_cost')
    list_filter = ('category',)
    search_fields = ('drug_code', 'name', 'category')
