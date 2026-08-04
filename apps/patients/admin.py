from django.contrib import admin
from .models import Patient

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('patient_code', 'animal_name', 'owner_name', 'species', 'lga', 'created_at')
    list_filter = ('species', 'lga')
    search_fields = ('patient_code', 'owner_name', 'animal_name')
