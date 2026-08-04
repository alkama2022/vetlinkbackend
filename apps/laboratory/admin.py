from django.contrib import admin
from .models import LabSample

@admin.register(LabSample)
class LabSampleAdmin(admin.ModelAdmin):
    list_display = ('sample_code', 'species', 'test', 'facility', 'status', 'priority', 'date_received')
    list_filter = ('status', 'priority', 'species')
    search_fields = ('sample_code', 'test', 'facility', 'species')
