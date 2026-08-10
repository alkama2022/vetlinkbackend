from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.payments.models import (
    Wallet, Invoice as PaymentInvoice, Payment, BankAccount, WithdrawalRequest,
)

User = get_user_model()


class PaymentsBase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="payuser@test.com", password="testpass123",
            user_type="VETERINARIAN", full_name="Pay User",
        )
        self.other = User.objects.create_user(
            email="payother@test.com", password="testpass123",
            user_type="FARMER", full_name="Pay Other",
        )
        self.client.force_authenticate(self.user)


class WalletTests(PaymentsBase):
    def test_wallet_list_auto_creates_wallet(self):
        res = self.client.get("/api/v1/payments/wallet/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 1)
        self.assertTrue(Wallet.objects.filter(user=self.user).exists())

    def test_wallet_is_scoped_to_user(self):
        Wallet.objects.create(user=self.other)
        res = self.client.get("/api/v1/payments/wallet/")
        self.assertEqual(res.data["count"], 1)


class PaymentListTests(PaymentsBase):
    def _make_invoice_and_payment(self, client_user, vet_user, invoice_number):
        invoice = PaymentInvoice.objects.create(
            invoice_number=invoice_number,
            client=client_user,
            veterinarian=vet_user,
            subtotal=5000,
            total=5000,
        )
        return Payment.objects.create(invoice=invoice, amount=5000, gateway_reference=f"ref-{invoice_number}")

    def test_payments_list_and_retrieve(self):
        self._make_invoice_and_payment(self.user, self.user, "INV-P1")
        res = self.client.get("/api/v1/payments/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 1)
        pid = res.data["results"][0]["id"]
        res = self.client.get(f"/api/v1/payments/{pid}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_payments_scoped_to_client_or_vet(self):
        self._make_invoice_and_payment(self.user, self.user, "INV-P2")
        self._make_invoice_and_payment(self.other, self.other, "INV-P3")
        res = self.client.get("/api/v1/payments/")
        self.assertEqual(res.data["count"], 1)


class BankAccountTests(PaymentsBase):
    def test_bank_account_crud(self):
        res = self.client.post(
            "/api/v1/payments/bank-accounts/",
            {"bank_name": "Access Bank", "account_number": "0123456789", "account_name": "Pay User"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(res.data["verified"])
        self.assertEqual(str(res.data["user"]), str(self.user.id))
        acc_id = res.data["id"]

        res = self.client.get("/api/v1/payments/bank-accounts/")
        self.assertEqual(res.data["count"], 1)

        res = self.client.delete(f"/api/v1/payments/bank-accounts/{acc_id}/")
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)


class WithdrawalTests(PaymentsBase):
    def setUp(self):
        super().setUp()
        self.wallet = Wallet.objects.create(user=self.user)
        self.bank = BankAccount.objects.create(
            user=self.user, bank_name="Access Bank", account_number="0123456789", verified=True,
        )

    def test_withdrawal_routes_not_shadowed_by_payments_router(self):
        res = self.client.get("/api/v1/payments/withdrawals/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_withdrawal_rejects_insufficient_balance(self):
        res = self.client.post(
            "/api/v1/payments/withdrawals/",
            {"bank_account": str(self.bank.id), "amount": 5000},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_withdrawal_creates_and_deducts_balance(self):
        self.wallet.available_balance = 20000
        self.wallet.save()
        res = self.client.post(
            "/api/v1/payments/withdrawals/",
            {"bank_account": str(self.bank.id), "amount": 5000},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["status"], "pending")
        self.assertEqual(res.data["bank_name"], "Access Bank")
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.available_balance, 15000)
        self.assertEqual(self.wallet.total_withdrawn, 5000)

    def test_withdrawal_rejects_foreign_bank_account(self):
        other_bank = BankAccount.objects.create(
            user=self.other, bank_name="GTBank", account_number="0987654321", verified=True,
        )
        self.wallet.available_balance = 20000
        self.wallet.save()
        res = self.client.post(
            "/api/v1/payments/withdrawals/",
            {"bank_account": str(other_bank.id), "amount": 5000},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_withdrawals_scoped_to_own_wallet(self):
        other_wallet = Wallet.objects.create(user=self.other)
        WithdrawalRequest.objects.create(wallet=other_wallet, bank_account=self.bank, amount=1000)
        res = self.client.get("/api/v1/payments/withdrawals/")
        self.assertEqual(res.data["count"], 0)


class InvoiceTests(PaymentsBase):
    def test_invoice_create_generates_number_and_client(self):
        res = self.client.post(
            "/api/v1/payments/invoices/",
            {"services": [{"description": "Consult", "amount": "5000"}], "subtotal": "5000", "total": "5000"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(res.data["invoice_number"].startswith("INV-"))
        self.assertEqual(str(res.data["client"]), str(self.user.id))

    def test_invoices_scoped_to_user(self):
        PaymentInvoice.objects.create(
            invoice_number="INV-OTH", client=self.other, subtotal=1, total=1,
        )
        res = self.client.get("/api/v1/payments/invoices/")
        self.assertEqual(res.data["count"], 0)

    def test_initialize_payment_returns_checkout_url(self):
        invoice = PaymentInvoice.objects.create(
            invoice_number="INV-INIT", client=self.user, subtotal=5000, total=5000,
        )
        res = self.client.post(
            "/api/v1/payments/initialize/",
            {"invoice": str(invoice.id), "amount": 5000, "idempotency_key": "key-1"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["checkout_url"], "https://stub.pay/checkout")
        self.assertTrue(Payment.objects.filter(invoice=invoice).exists())

    def test_cannot_initialize_foreign_invoice(self):
        invoice = PaymentInvoice.objects.create(
            invoice_number="INV-FOREIGN", client=self.other, subtotal=5000, total=5000,
        )
        res = self.client.post(
            "/api/v1/payments/initialize/",
            {"invoice": str(invoice.id), "amount": 5000, "idempotency_key": "key-2"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
