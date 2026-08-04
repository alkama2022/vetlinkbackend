from django.contrib import admin
from .models import Notification

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('notif_code', 'title', 'tone', 'read', 'created_at_override')
    list_filter = ('tone', 'read')
    search_fields = ('notif_code', 'title', 'body')
