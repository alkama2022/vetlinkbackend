from django.contrib import admin
from .models import FarmerHerd, FarmerReminder

@admin.register(FarmerHerd)
class FarmerHerdAdmin(admin.ModelAdmin):
    list_display = ('herd_code', 'type', 'count', 'healthy')
    list_filter = ('type',)

@admin.register(FarmerReminder)
class FarmerReminderAdmin(admin.ModelAdmin):
    list_display = ('reminder_code', 'title', 'date', 'tone', 'done')
    list_filter = ('tone', 'done')
