from rest_framework import serializers
from .models import (
    Wallet, WalletTransaction, Invoice, Payment, Receipt, BankAccount, WithdrawalRequest, PaymentGateway, Refund
)


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ('id', 'available_balance', 'pending_balance', 'total_earnings', 'total_withdrawn')


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = ('id', 'invoice_number', 'client', 'veterinarian', 'services', 'subtotal', 'taxes', 'total', 'status', 'created_at')
        read_only_fields = ('invoice_number', 'client', 'status', 'created_at')
        extra_kwargs = {
            'veterinarian': {'required': False, 'allow_null': True},
        }


class PaymentSerializer(serializers.ModelSerializer):
    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True)

    class Meta:
        model = Payment
        fields = ('id', 'invoice', 'amount', 'gateway', 'gateway_reference', 'status', 'idempotency_key', 'metadata', 'created_at')
        read_only_fields = ('status', 'gateway_reference', 'created_at')


def _mask_account_number(acc: str) -> str:
    acc = (acc or "").strip().replace(" ", "")
    if len(acc) <= 4:
        return "****"
    return "*" * (len(acc) - 4) + acc[-4:]


class BankAccountSerializer(serializers.ModelSerializer):
    account_number_masked = serializers.SerializerMethodField()

    class Meta:
        model = BankAccount
        fields = ('id', 'user', 'bank_name', 'account_number', 'account_number_masked', 'account_name', 'verified')
        read_only_fields = ('verified', 'user')
        extra_kwargs = {'account_number': {'write_only': True}}

    def get_account_number_masked(self, obj):
        return _mask_account_number(obj.account_number)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Never leak full account_number in list responses; only masked version
        # Keep write_only behavior: remove raw if present and replace with masked alias
        if 'account_number' in data:
            data.pop('account_number', None)
        return data


class WithdrawalRequestSerializer(serializers.ModelSerializer):
    bank_name = serializers.CharField(source='bank_account.bank_name', read_only=True)
    account_number = serializers.SerializerMethodField()

    def get_account_number(self, obj):
        return _mask_account_number(obj.bank_account.account_number) if getattr(obj, 'bank_account', None) else ""

    class Meta:
        model = WithdrawalRequest
        fields = ('id', 'wallet', 'bank_account', 'bank_name', 'account_number', 'amount', 'status', 'provider_reference', 'created_at')
        read_only_fields = ('wallet', 'bank_name', 'account_number', 'status', 'provider_reference', 'created_at')


class RefundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Refund
        fields = ('id', 'payment', 'requester', 'amount', 'reason', 'status', 'created_at', 'processed_at')
        read_only_fields = ('requester', 'status', 'created_at', 'processed_at')
