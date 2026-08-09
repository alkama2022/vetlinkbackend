import uuid

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
    # The serializer exposes invoice_code as the public id, so lookups use the code.
    lookup_field = 'invoice_code'
    lookup_value_regex = '[^/.]+'
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status']
    search_fields = ['invoice_code', 'owner_name', 'animal']
    ordering_fields = ['created_at', 'total', 'status']

    @action(detail=True, methods=['post'], url_path='pay')
    def mark_paid(self, request, invoice_code=None):
        invoice = self.get_object()
        invoice.status = Invoice.StatusChoices.PAID
        invoice.paid_at = timezone.now()
        invoice.save(update_fields=['status', 'paid_at'])
        return Response(InvoiceSerializer(invoice).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='waive')
    def mark_waived(self, request, invoice_code=None):
        invoice = self.get_object()
        invoice.status = Invoice.StatusChoices.WAIVED
        invoice.save(update_fields=['status'])
        return Response(InvoiceSerializer(invoice).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='checkout')
    def checkout(self, request, invoice_code=None):
        """Start a gateway payment for a clinic invoice.

        Creates (or reuses) the payments-side invoice for this billing
        invoice, then initializes the payment through the active gateway.
        Returns the checkout URL + payment reference for the frontend.
        """
        from apps.payments.gateways import get_gateway_provider
        from apps.payments.models import Invoice as PaymentInvoice
        from apps.payments.models import Payment, PaymentGateway

        invoice = self.get_object()
        if invoice.status == Invoice.StatusChoices.PAID:
            return Response(
                {'detail': 'Invoice is already paid.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        services = list(invoice.services.values('description', 'amount'))
        payment_invoice, created = PaymentInvoice.objects.get_or_create(
            invoice_number=invoice.invoice_code,
            defaults={
                'client': request.user,
                'veterinarian': request.user,
                'services': services,
                'subtotal': invoice.total,
                'total': invoice.total,
            },
        )
        if not created:
            payment_invoice.services = services
            payment_invoice.subtotal = invoice.total
            payment_invoice.total = invoice.total
            payment_invoice.save()

        gateway = PaymentGateway.objects.filter(enabled=True).first()
        gateway_provider = get_gateway_provider(gateway)
        idempotency_key = request.data.get('idempotency_key') or uuid.uuid4().hex
        metadata = {
            'invoice': str(payment_invoice.id),
            'billing_invoice': str(invoice.id),
            'tx_ref': idempotency_key,
            'customer_email': getattr(request.user, 'email', ''),
            'customer_name': str(request.user),
            'redirect_url': request.data.get('redirect_url', ''),
            'title': f'Invoice {invoice.invoice_code}',
            'description': f'Payment for clinic invoice {invoice.invoice_code}',
        }

        payload = gateway_provider.initialize_payment(
            amount=invoice.total,
            currency='NGN',
            metadata=metadata,
            idempotency_key=idempotency_key,
        )
        gateway_reference = payload.get('reference') or payload.get('transaction_id') or idempotency_key
        payment = Payment.objects.create(
            invoice=payment_invoice,
            amount=invoice.total,
            gateway=gateway,
            gateway_reference=gateway_reference,
            status='pending',
            idempotency_key=idempotency_key,
            metadata=metadata,
        )

        return Response({
            'checkout_url': payload.get('checkout_url'),
            'payment_id': str(payment.id),
            'reference': gateway_reference,
        })
