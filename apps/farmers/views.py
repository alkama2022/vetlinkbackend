from rest_framework import viewsets, permissions
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import FarmerHerd, FarmerReminder
from .serializers import FarmerHerdSerializer, FarmerReminderSerializer


class FarmerHerdViewSet(viewsets.ModelViewSet):
    queryset = FarmerHerd.objects.all().order_by('-created_at')
    serializer_class = FarmerHerdSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['type']
    search_fields = ['herd_code', 'type', 'count']
    ordering_fields = ['created_at', 'healthy']


class FarmerReminderViewSet(viewsets.ModelViewSet):
    queryset = FarmerReminder.objects.all().order_by('date')
    serializer_class = FarmerReminderSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['done', 'tone']
    search_fields = ['reminder_code', 'title', 'date']
    ordering_fields = ['date', 'done']
