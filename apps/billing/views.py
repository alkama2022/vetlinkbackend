from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Invoice
from .serializers import InvoiceSerializer
from apps.core.permissions import IsClinicStaffOrAdmin


class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.all().prefetch_related('services').order_by('-created_at')
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated, IsClinicStaffOrAdmin]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status']
    search_fields = ['invoice_code', 'owner_name', 'animal']
    ordering_fields = ['created_at', 'total', 'status']

    @action(detail=True, methods=['post'], url_path='pay')
    def mark_paid(self, request, pk=None):
        invoice = self.get_object()
        invoice.status = Invoice.StatusChoices.PAID
        invoice.paid_at = timezone.now()
        invoice.save(update_fields=['status', 'paid_at'])
        return Response(InvoiceSerializer(invoice).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='waive')
    def mark_waived(self, request, pk=None):
        invoice = self.get_object()
        invoice.status = Invoice.StatusChoices.WAIVED
        invoice.save(update_fields=['status'])
        return Response(InvoiceSerializer(invoice).data, status=status.HTTP_200_OK)
