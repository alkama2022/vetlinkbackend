from django.contrib import admin
from .models import (
    Wallet, WalletTransaction, Invoice, Payment, Receipt, BankAccount, WithdrawalRequest, PaymentGateway, Refund, FinancialAuditLog
)


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'available_balance', 'pending_balance', 'total_earnings', 'total_withdrawn')


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'client', 'veterinarian', 'total', 'status', 'created_at')
    search_fields = ('invoice_number', 'client__email')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'amount', 'gateway', 'status', 'created_at')
    search_fields = ('gateway_reference',)


@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = ('wallet', 'amount', 'status', 'created_at')
    list_filter = ('status',)


@admin.register(FinancialAuditLog)
class FinancialAuditLogAdmin(admin.ModelAdmin):
    list_display = ('actor', 'action', 'resource', 'created_at')
