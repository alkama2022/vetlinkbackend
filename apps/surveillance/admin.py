from django.contrib import admin
from .models import DiseaseReport

@admin.register(DiseaseReport)
class DiseaseReportAdmin(admin.ModelAdmin):
    list_display = ('report_code', 'disease', 'species', 'lga', 'affected', 'dead', 'alert_status', 'submitted_at')
    list_filter = ('alert_status', 'species', 'lga')
    search_fields = ('report_code', 'disease', 'species', 'location', 'farmer_name')
