import random
import time

from rest_framework import viewsets, permissions
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import FarmerHerd, FarmerReminder
from .serializers import FarmerHerdSerializer, FarmerReminderSerializer


def _unique_code(prefix, model, field='code'):
    while True:
        candidate = f"{prefix}{str(int(time.time() * 1000) + random.randint(0, 999))[-6:]}"
        if not model.objects.filter(**{field: candidate}).exists():
            return candidate


class FarmerHerdViewSet(viewsets.ModelViewSet):
    serializer_class = FarmerHerdSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'herd_code'
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['type']
    search_fields = ['herd_code', 'type', 'count']
    ordering_fields = ['created_at', 'healthy']

    def get_queryset(self):
        return FarmerHerd.objects.filter(farmer=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(
            farmer=self.request.user,
            herd_code=_unique_code('H', FarmerHerd, 'herd_code'),
        )


class FarmerReminderViewSet(viewsets.ModelViewSet):
    serializer_class = FarmerReminderSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'reminder_code'
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['done', 'tone']
    search_fields = ['reminder_code', 'title', 'date']
    ordering_fields = ['date', 'done']

    def get_queryset(self):
        return FarmerReminder.objects.filter(farmer=self.request.user).order_by('date')

    def perform_create(self, serializer):
        serializer.save(
            farmer=self.request.user,
            reminder_code=_unique_code('R', FarmerReminder, 'reminder_code'),
        )
