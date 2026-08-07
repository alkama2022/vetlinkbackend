import uuid

from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes

from .models import Wallet, WalletTransaction, Invoice, Payment, PaymentGateway, WithdrawalRequest, BankAccount, Receipt, FinancialAuditLog
from .serializers import WalletSerializer, InvoiceSerializer, PaymentSerializer, WithdrawalRequestSerializer, BankAccountSerializer
from .gateways import get_gateway_provider, StubGateway
from apps.notifications.models import Notification


class WalletViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Wallet.objects.select_related('user')
    serializer_class = WalletSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        # always return current user's wallet
        wallet, _ = Wallet.objects.get_or_create(user=self.request.user)
        return wallet


class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = (IsAuthenticated,)

    def perform_create(self, serializer):
        invoice = serializer.save()
        # create initial FinancialAuditLog
        FinancialAuditLog.objects.create(actor=self.request.user, action='invoice.created', resource=str(invoice.id), metadata={'invoice_number': invoice.invoice_number})


class PaymentViewSet(viewsets.GenericViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = (IsAuthenticated,)

    @action(detail=False, methods=['post'])
    def initialize(self, request):
        """Start a payment for an invoice. Returns checkout url and reference."""
        serializer = PaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invoice = get_object_or_404(Invoice, id=serializer.validated_data['invoice'].id)
        amount = serializer.validated_data.get('amount') or invoice.total

        # idempotency handling
        idempotency_key = serializer.validated_data.get('idempotency_key') or request.headers.get('Idempotency-Key')

        gateway = PaymentGateway.objects.filter(enabled=True).first()
        gateway_provider = get_gateway_provider(gateway)
        tx_ref = serializer.validated_data.get('idempotency_key') or uuid.uuid4().hex
        metadata = {
            'invoice': str(invoice.id),
            'tx_ref': tx_ref,
            'customer_email': getattr(request.user, 'email', ''),
            'customer_name': str(request.user),
            'redirect_url': request.data.get('redirect_url', ''),
            'title': f'Invoice {invoice.invoice_number}',
            'description': f'Payment for invoice {invoice.invoice_number}',
        }

        payload = gateway_provider.initialize_payment(
            amount=amount,
            currency='NGN',
            metadata=metadata,
            idempotency_key=idempotency_key,
        )

        gateway_reference = payload.get('reference') or payload.get('transaction_id') or tx_ref
        payment = Payment.objects.create(
            invoice=invoice,
            amount=amount,
            gateway=gateway if gateway else None,
            gateway_reference=gateway_reference,
            status='pending',
            idempotency_key=idempotency_key or tx_ref,
            metadata=metadata,
        )

        return Response({
            'checkout_url': payload.get('checkout_url'),
            'payment_id': str(payment.id),
            'reference': gateway_reference,
        })


@extend_schema(request=None, responses={200: OpenApiTypes.OBJECT})
@api_view(['POST'])
@permission_classes([])
def gateway_webhook(request):
    data = request.data
    ref = (
        data.get('reference')
        or data.get('transaction_id')
        or data.get('data', {}).get('id')
        or data.get('data', {}).get('tx_ref')
    )
    if not ref:
        return Response(status=400)

    payment = Payment.objects.filter(gateway_reference=ref).first()
    if not payment:
        payment = Payment.objects.filter(metadata__tx_ref=ref).first()
    if not payment:
        return Response(status=404)

    gateway_provider = get_gateway_provider(payment.gateway)
    if not gateway_provider.verify_webhook(request):
        return Response(status=400)

    try:
        transaction_data = gateway_provider.verify_transaction(payment.gateway_reference)
    except Exception:
        return Response(status=400)

    if payment.status != 'successful':
        payment.status = 'successful'
        payment.metadata = {**payment.metadata, 'gateway_payload': transaction_data}
        payment.save()

        invoice = payment.invoice
        invoice.status = 'paid'
        invoice.save()

        vet = invoice.veterinarian
        if vet:
            wallet, _ = Wallet.objects.get_or_create(user=vet)
            wallet.pending_balance += payment.amount
            wallet.total_earnings += payment.amount
            wallet.save()

            FinancialAuditLog.objects.create(
                actor=None,
                action='payment.settled',
                resource=str(payment.id),
                metadata={'amount': str(payment.amount)},
            )

            Notification.objects.create(
                notif_code=f'PAY_{payment.id.hex[:8]}',
                title='Payment received',
                body=f'A payment of {payment.amount} was received for invoice {invoice.invoice_number}',
                tone=Notification.ToneChoices.SUCCESS,
                recipient=vet,
            )

    return Response({'status': 'ok'})


class WithdrawalRequestViewSet(viewsets.ModelViewSet):
    queryset = WithdrawalRequest.objects.all()
    serializer_class = WithdrawalRequestSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        # vets see own withdrawals; admins see all
        if user.is_superuser:
            return self.queryset
        wallet = getattr(user, 'wallet', None)
        if wallet:
            return self.queryset.filter(wallet=wallet)
        return self.queryset.none()

    def perform_create(self, serializer):
        wallet = getattr(self.request.user, 'wallet', None)
        if not wallet:
            raise Exception('No wallet available')
        amount = serializer.validated_data['amount']
        if amount > wallet.available_balance:
            raise Exception('Insufficient balance')

        with transaction.atomic():
            # deduct available balance
            wallet.available_balance -= amount
            wallet.save()
            wr = serializer.save(wallet=wallet)
            FinancialAuditLog.objects.create(actor=self.request.user, action='withdrawal.requested', resource=str(wr.id), metadata={'amount': str(amount)})
            Notification.objects.create(notif_code=f'WD_{wr.id.hex[:8]}', title='Withdrawal requested', body=f'Withdrawal of {amount} requested', tone=Notification.ToneChoices.INFO, recipient=self.request.user)
