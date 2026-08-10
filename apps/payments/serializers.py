from rest_framework import serializers
from .models import (
    Wallet, WalletTransaction, Invoice, Payment, Receipt, BankAccount, WithdrawalRequest, PaymentGateway
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


class BankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = ('id', 'user', 'bank_name', 'account_number', 'account_name', 'verified')
        read_only_fields = ('verified', 'user')


class WithdrawalRequestSerializer(serializers.ModelSerializer):
    bank_name = serializers.CharField(source='bank_account.bank_name', read_only=True)
    account_number = serializers.CharField(source='bank_account.account_number', read_only=True)

    class Meta:
        model = WithdrawalRequest
        fields = ('id', 'wallet', 'bank_account', 'bank_name', 'account_number', 'amount', 'status', 'provider_reference', 'created_at')
        read_only_fields = ('wallet', 'bank_name', 'account_number', 'status', 'provider_reference', 'created_at')
