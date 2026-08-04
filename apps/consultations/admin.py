from django.contrib import admin
from .models import ConsultationRequest, ChatMessage

class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0

@admin.register(ConsultationRequest)
class ConsultationRequestAdmin(admin.ModelAdmin):
    list_display = ('consultation_code', 'farmer_name', 'vet_name', 'species', 'severity', 'status', 'channel')
    list_filter = ('status', 'severity', 'channel')
    search_fields = ('consultation_code', 'farmer_name', 'vet_name', 'disease_name')
    inlines = [ChatMessageInline]
