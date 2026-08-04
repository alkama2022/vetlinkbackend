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
        read_only_fields = ('invoice_number', 'status', 'created_at')


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ('id', 'invoice', 'amount', 'gateway', 'gateway_reference', 'status', 'idempotency_key', 'metadata', 'created_at')
        read_only_fields = ('status', 'gateway_reference', 'created_at')


class BankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = ('id', 'user', 'bank_name', 'account_number', 'account_name', 'verified')
        read_only_fields = ('verified',)


class WithdrawalRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = WithdrawalRequest
        fields = ('id', 'wallet', 'bank_account', 'amount', 'status', 'provider_reference', 'created_at')
        read_only_fields = ('status', 'provider_reference', 'created_at')
