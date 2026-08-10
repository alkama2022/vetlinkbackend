import uuid

from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes

from .models import Wallet, WalletTransaction, Invoice, Payment, PaymentGateway, WithdrawalRequest, BankAccount, Receipt, FinancialAuditLog
from .serializers import WalletSerializer, InvoiceSerializer, PaymentSerializer, WithdrawalRequestSerializer, BankAccountSerializer
from .gateways import get_gateway_provider, FlutterwaveGateway, StubGateway
from apps.notifications.models import Notification
from rest_framework.exceptions import PermissionDenied, ValidationError


def _unique_invoice_number():
    while True:
        candidate = f"INV-{str(uuid.uuid4().hex)[:10].upper()}"
        if not Invoice.objects.filter(invoice_number=candidate).exists():
            return candidate


class WalletViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Wallet.objects.select_related('user')
    serializer_class = WalletSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        # ensure a wallet row exists so the user always sees one
        Wallet.objects.get_or_create(user=self.request.user)
        return self.queryset.filter(user=self.request.user)

    def get_object(self):
        # always return current user's wallet
        wallet, _ = Wallet.objects.get_or_create(user=self.request.user)
        return wallet


class BankAccountViewSet(viewsets.ModelViewSet):
    queryset = BankAccount.objects.all()
    serializer_class = BankAccountSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, verified=True)


class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.user_type in ('SYSTEM_ADMIN', 'SUPER_ADMIN'):
            return self.queryset
        return self.queryset.filter(Q(client=user) | Q(veterinarian=user)).distinct()

    def perform_create(self, serializer):
        invoice = serializer.save(
            client=self.request.user,
            invoice_number=_unique_invoice_number(),
        )
        # create initial FinancialAuditLog
        FinancialAuditLog.objects.create(actor=self.request.user, action='invoice.created', resource=str(invoice.id), metadata={'invoice_number': invoice.invoice_number})


class PaymentViewSet(viewsets.GenericViewSet):
    queryset = Payment.objects.select_related('invoice').all()
    serializer_class = PaymentSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.user_type in ('SYSTEM_ADMIN', 'SUPER_ADMIN'):
            return self.queryset
        return self.queryset.filter(
            Q(invoice__client=user) | Q(invoice__veterinarian=user)
        ).distinct()

    def list(self, request):
        queryset = self.filter_queryset(self.get_queryset()).order_by('-created_at')
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = PaymentSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = PaymentSerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        payment = self.get_object()
        serializer = PaymentSerializer(payment)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def initialize(self, request):
        """Start a payment for an invoice. Returns checkout url and reference."""
        serializer = PaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invoice = get_object_or_404(Invoice, id=serializer.validated_data['invoice'].id)

        # Authorization: a user may only pay their own invoices. Otherwise any
        # authenticated user could settle (or at least enumerate) other
        # customers' bills.
        if str(invoice.client_id) != str(request.user.id):
            raise PermissionDenied('You can only pay your own invoices.')
        if invoice.status == 'paid':
            raise ValidationError({'invoice': 'This invoice has already been paid.'})
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
    # SECURITY: the stub gateway trusts every webhook unconditionally, so a
    # public webhook endpoint backed by it would let anyone mark payments as
    # successful. In production only signed webhooks from a real gateway are
    # acceptable; the endpoint is simply disabled otherwise.
    if isinstance(gateway_provider, StubGateway):
        return Response({'detail': 'Payments disabled: no live gateway configured.'}, status=503)
    if not gateway_provider.verify_webhook(request):
        return Response(status=400)

    try:
        transaction_data = gateway_provider.verify_transaction(payment.gateway_reference)
    except Exception:
        return Response(status=400)

    with transaction.atomic():
        # Re-fetch under lock to make the success path idempotent and safe
        # under concurrent webhook deliveries.
        payment = Payment.objects.select_for_update().get(pk=payment.pk)
        if payment.status != 'successful':
            payment.status = 'successful'
            payment.metadata = {**payment.metadata, 'gateway_payload': transaction_data}
            payment.save()

        invoice = payment.invoice
        invoice.status = 'paid'
        invoice.save()

        # Mark the originating clinic invoice as paid when this payment
        # came through the billing checkout flow.
        billing_invoice_id = payment.metadata.get('billing_invoice')
        if billing_invoice_id:
            from apps.billing.models import Invoice as BillingInvoice
            BillingInvoice.objects.filter(id=billing_invoice_id, status='Unpaid').update(
                status='Paid', paid_at=timezone.now()
            )

        vet = invoice.veterinarian
        if vet:
            wallet, _ = Wallet.objects.select_for_update().get_or_create(user=vet)
            # Funds become immediately withdrawable on confirmation. There is
            # no settlement/escrow step in the current product, so crediting
            # pending_balance would strand earnings forever.
            wallet.available_balance += payment.amount
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
            raise ValidationError({'wallet': 'No wallet available.'})
        amount = serializer.validated_data['amount']
        if amount <= 0:
            raise ValidationError({'amount': 'Amount must be greater than zero.'})
        if amount > wallet.available_balance:
            raise ValidationError({'amount': 'Insufficient balance.'})

        # The bank account must belong to the withdrawing user, otherwise a
        # user could route withdrawals to someone else's account.
        bank_account = serializer.validated_data.get('bank_account')
        if bank_account and bank_account.user_id != self.request.user.id:
            raise ValidationError({'bank_account': 'Invalid bank account.'})

        with transaction.atomic():
            # Serializer.save() runs model validation again inside the
            # transaction so we re-check the balance atomically.
            wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)
            if amount > wallet.available_balance:
                raise ValidationError({'amount': 'Insufficient balance.'})
            # deduct available balance
            wallet.available_balance -= amount
            wallet.total_withdrawn += amount
            wallet.save()
            wr = serializer.save(wallet=wallet)
            FinancialAuditLog.objects.create(actor=self.request.user, action='withdrawal.requested', resource=str(wr.id), metadata={'amount': str(amount)})
            Notification.objects.create(notif_code=f'WD_{wr.id.hex[:8]}', title='Withdrawal requested', body=f'Withdrawal of {amount} requested', tone=Notification.ToneChoices.INFO, recipient=self.request.user)
