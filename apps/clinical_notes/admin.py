from django.contrib import admin
from .models import CaseNote

@admin.register(CaseNote)
class CaseNoteAdmin(admin.ModelAdmin):
    list_display = ('note_code', 'owner_name', 'animal', 'vet_name', 'diagnosis', 'date')
    search_fields = ('note_code', 'owner_name', 'animal', 'vet_name', 'diagnosis')
