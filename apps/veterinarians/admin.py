from django.contrib import admin
from .models import VeterinarianProfile


@admin.register(VeterinarianProfile)
class VeterinarianProfileAdmin(admin.ModelAdmin):
    list_display = ('vet_code', 'full_name', 'license_number', 'clinic_name', 'lga', 'available', 'rating')
    list_filter = ('available', 'available_online', 'available_emergency', 'lga')
    search_fields = ('full_name', 'license_number', 'clinic_name', 'lga')
    ordering = ('-rating',)
