import random
import time

from rest_framework import viewsets, permissions
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import CaseNote
from .serializers import CaseNoteSerializer


def _unique_code(prefix, model, field='code'):
    while True:
        candidate = f"{prefix}{str(int(time.time() * 1000) + random.randint(0, 999))[-6:]}"
        if not model.objects.filter(**{field: candidate}).exists():
            return candidate


class CaseNoteViewSet(viewsets.ModelViewSet):
    queryset = CaseNote.objects.all().order_by('-created_at')
    serializer_class = CaseNoteSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'note_code'
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['note_code', 'owner_name', 'animal', 'vet_name', 'diagnosis', 'treatment']
    ordering_fields = ['date', 'created_at']

    def get_queryset(self):
        qs = CaseNote.objects.all().order_by('-created_at')
        user = self.request.user
        if user.is_superuser or user.user_type in ('SYSTEM_ADMIN', 'SUPER_ADMIN'):
            return qs
        return qs

    def perform_create(self, serializer):
        serializer.save(note_code=_unique_code('N', CaseNote, 'note_code'))
