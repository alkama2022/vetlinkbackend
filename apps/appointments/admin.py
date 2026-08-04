from django.contrib import admin
from .models import Appointment

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('appointment_code', 'owner_name', 'animal', 'date', 'time', 'status')
    list_filter = ('status', 'date')
    search_fields = ('appointment_code', 'owner_name', 'animal', 'reason')
