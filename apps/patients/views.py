import random
import time

from rest_framework import viewsets, permissions
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Patient
from .serializers import PatientSerializer


def _unique_code(prefix, model, field='code'):
    while True:
        candidate = f"{prefix}{str(int(time.time() * 1000) + random.randint(0, 999))[-6:]}"
        if not model.objects.filter(**{field: candidate}).exists():
            return candidate


class PatientViewSet(viewsets.ModelViewSet):
    queryset = Patient.objects.all().order_by('-created_at')
    serializer_class = PatientSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'patient_code'
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['species', 'lga']
    search_fields = ['patient_code', 'owner_name', 'owner_phone', 'animal_name', 'lga', 'species']
    ordering_fields = ['created_at', 'owner_name', 'animal_name']

    def get_queryset(self):
        qs = Patient.objects.all().order_by('-created_at')
        user = self.request.user
        if user.is_superuser or user.user_type in ('SYSTEM_ADMIN', 'SUPER_ADMIN'):
            return qs
        return qs

    def perform_create(self, serializer):
        serializer.save(
            patient_code=_unique_code('P', Patient, 'patient_code'),
            created_by=self.request.user,
        )
