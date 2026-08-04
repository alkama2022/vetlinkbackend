from rest_framework import viewsets, permissions
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import CaseNote
from .serializers import CaseNoteSerializer


class CaseNoteViewSet(viewsets.ModelViewSet):
    queryset = CaseNote.objects.all().order_by('-created_at')
    serializer_class = CaseNoteSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['note_code', 'owner_name', 'animal', 'vet_name', 'diagnosis', 'treatment']
    ordering_fields = ['date', 'created_at']
