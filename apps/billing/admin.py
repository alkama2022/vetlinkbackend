from django.contrib import admin
from .models import Invoice, InvoiceItem

class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_code', 'owner_name', 'animal', 'total', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('invoice_code', 'owner_name', 'animal')
    inlines = [InvoiceItemInline]
