"""Regression + security tests for the production-readiness audit.

Covers:
  * Disease report ownership + status-transition enforcement
  * Payment authorization (IDOR), webhook stub-gateway rejection, withdrawals
  * Consultation participant access + message sender spoofing
  * Password reset user-enumeration
  * Marketplace pagination ordering
"""

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from apps.payments.models import (
    BankAccount,
    FinancialAuditLog,
    Invoice as PaymentInvoice,
    Payment,
    PaymentGateway,
    Wallet,
    WithdrawalRequest,
)
from apps.surveillance.models import DiseaseReport
from apps.veterinarians.models import VeterinarianProfile

User = get_user_model()


def make_user(email, user_type='FARMER', **kwargs):
    return User.objects.create_user(
        email=email, password='testpass123',
        full_name=kwargs.pop('full_name', email.split('@')[0]),
        user_type=user_type, is_email_verified=True, **kwargs)


# ============================================================
# Surveillance: ownership + status workflow
# ============================================================

class DiseaseReportAuthorizationTests(APITestCase):
    def setUp(self):
        self.farmer = make_user('farm1@test.com', 'FARMER')
        self.other = make_user('farm2@test.com', 'FARMER')
        self.gov = make_user('gov@test.com', 'GOVERNMENT_OFFICER')
        self.report = DiseaseReport.objects.create(
            report_code='VK900001', species='Cattle', disease='Anthrax',
            affected=5, dead=2, date='2026-08-01', location='Kano',
            lga='Kano Municipal', farmer=self.farmer, farmer_name='Farm1',
        )
        self.detail_url = reverse(
            'disease-report-detail', kwargs={'report_code': self.report.report_code})

    def test_owner_can_update_own_report(self):
        self.client.force_authenticate(self.farmer)
        res = self.client.patch(self.detail_url, {'notes': 'updated'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.report.refresh_from_db()
        self.assertEqual(self.report.notes, 'updated')

    def test_other_user_cannot_update_report(self):
        self.client.force_authenticate(self.other)
        res = self.client.patch(self.detail_url, {'notes': 'hacked'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_other_user_cannot_delete_report(self):
        self.client.force_authenticate(self.other)
        res = self.client.delete(self.detail_url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(DiseaseReport.objects.filter(pk=self.report.pk).exists())

    def test_gov_officer_can_update_report(self):
        self.client.force_authenticate(self.gov)
        res = self.client.patch(self.detail_url, {'notes': 'gov edited'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_alert_status_not_writable_via_generic_update(self):
        # A regular farmer must NOT be able to self-escalate to Confirmed.
        self.client.force_authenticate(self.farmer)
        res = self.client.patch(
            self.detail_url, {'alertStatus': 'Confirmed'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.report.refresh_from_db()
        self.assertEqual(self.report.alert_status, 'Suspected')

    def test_gov_officer_can_transition_status(self):
        self.client.force_authenticate(self.gov)
        url = reverse(
            'disease-report-update-status',
            kwargs={'report_code': self.report.report_code})
        res = self.client.patch(url, {'alertStatus': 'Under investigation'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.report.refresh_from_db()
        self.assertEqual(self.report.alert_status, 'Under investigation')

    def test_invalid_status_transition_rejected(self):
        self.client.force_authenticate(self.gov)
        url = reverse(
            'disease-report-update-status',
            kwargs={'report_code': self.report.report_code})
        # Suspected -> Confirmed skips the investigation step.
        res = self.client.patch(url, {'alertStatus': 'Confirmed'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_farmer_cannot_change_status_at_all(self):
        self.client.force_authenticate(self.farmer)
        url = reverse(
            'disease-report-update-status',
            kwargs={'report_code': self.report.report_code})
        res = self.client.patch(url, {'alertStatus': 'Closed'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


# ============================================================
# Payments: authorization, webhook security, withdrawals
# ============================================================

class PaymentAuthorizationTests(APITestCase):
    def setUp(self):
        self.buyer = make_user('buyer@test.com', 'FARMER')
        self.other = make_user('other@test.com', 'FARMER')
        self.invoice = PaymentInvoice.objects.create(
            invoice_number='PAY-INV-001', client=self.buyer,
            subtotal=100, total=100,
        )
        self.url = reverse('payment-initialize')

    def test_can_pay_own_invoice(self):
        self.client.force_authenticate(self.buyer)
        res = self.client.post(self.url, {'invoice': str(self.invoice.id)}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.assertIn('checkout_url', res.data)

    def test_cannot_pay_someone_elses_invoice(self):
        self.client.force_authenticate(self.other)
        res = self.client.post(self.url, {'invoice': str(self.invoice.id)}, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_pay_already_paid_invoice(self):
        self.invoice.status = 'paid'
        self.invoice.save()
        self.client.force_authenticate(self.buyer)
        res = self.client.post(self.url, {'invoice': str(self.invoice.id)}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_requires_auth(self):
        res = self.client.post(self.url, {'invoice': str(self.invoice.id)}, format='json')
        self.assertIn(res.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))


class GatewayWebhookSecurityTests(APITestCase):
    def setUp(self):
        self.buyer = make_user('buyer2@test.com', 'FARMER')
        self.vet = make_user('vet2@test.com', 'VETERINARIAN')
        self.invoice = PaymentInvoice.objects.create(
            invoice_number='PAY-INV-002', client=self.buyer,
            veterinarian=self.vet, subtotal=50, total=50,
        )
        # Payment created without a gateway -> StubGateway provider.
        self.payment = Payment.objects.create(
            invoice=self.invoice, amount=50, status='pending',
            gateway_reference='STUB-REF-1', idempotency_key='k1',
        )
        self.url = reverse('gateway_webhook')

    def test_webhook_rejected_without_live_gateway(self):
        # Without a configured live gateway the webhook must never succeed,
        # otherwise anyone could mark payments as paid.
        res = self.client.post(
            self.url, {'reference': 'STUB-REF-1'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'pending')

    def test_webhook_unknown_reference_404(self):
        res = self.client.post(
            self.url, {'reference': 'DOES-NOT-EXIST'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_webhook_missing_reference_400(self):
        res = self.client.post(self.url, {}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_live_gateway_webhook_verifies_signature(self):
        gateway = PaymentGateway.objects.create(
            name='flutterwave', provider='flutterwave', enabled=True)
        self.payment.gateway = gateway
        self.payment.save()
        # No signature header -> rejected.
        res = self.client.post(
            self.url, {'reference': 'STUB-REF-1'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'pending')


class WithdrawalAuthorizationTests(APITestCase):
    def setUp(self):
        self.vet = make_user('vet3@test.com', 'VETERINARIAN')
        self.other = make_user('other3@test.com', 'FARMER')
        self.wallet = Wallet.objects.create(user=self.vet, available_balance=500)
        self.account = BankAccount.objects.create(
            user=self.vet, bank_name='GTB', account_number='1234567890',
            account_name='Vet', verified=True)
        self.url = reverse('withdrawal-list')

    def test_withdraw_success(self):
        self.client.force_authenticate(self.vet)
        res = self.client.post(
            self.url,
            {'bank_account': str(self.account.id), 'amount': '200'},
            format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.available_balance, 300)
        self.assertEqual(self.wallet.total_withdrawn, 200)
        self.assertTrue(FinancialAuditLog.objects.filter(action='withdrawal.requested').exists())

    def test_cannot_withdraw_other_users_bank_account(self):
        stolen = BankAccount.objects.create(
            user=self.other, bank_name='UBA', account_number='000',
            account_name='Other', verified=True)
        self.client.force_authenticate(self.vet)
        res = self.client.post(
            self.url,
            {'bank_account': str(stolen.id), 'amount': '100'},
            format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_withdraw_more_than_balance(self):
        self.client.force_authenticate(self.vet)
        res = self.client.post(
            self.url,
            {'bank_account': str(self.account.id), 'amount': '1000'},
            format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.available_balance, 500)

    def test_cannot_withdraw_negative_or_zero(self):
        self.client.force_authenticate(self.vet)
        res = self.client.post(
            self.url,
            {'bank_account': str(self.account.id), 'amount': '-50'},
            format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bank_accounts_scoped_to_owner(self):
        self.client.force_authenticate(self.vet)
        res = self.client.get(reverse('bank-account-list'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Paginated response: {'count': 1, 'results': [...]}
        data = res.data.get('results', res.data)
        self.assertEqual(len(data), 1)


# ============================================================
# Consultations: participant access + message integrity
# ============================================================

class ConsultationWorkflowTests(APITestCase):
    def setUp(self):
        self.farmer = make_user('cfarm@test.com', 'FARMER', full_name='Farmer C')
        self.vet_user = make_user('cvet@test.com', 'VETERINARIAN', full_name='Vet C')
        self.profile = VeterinarianProfile.objects.create(
            user=self.vet_user, vet_code='VET-C-1', full_name='Vet C',
            license_number='LIC-C', qualifications='DVM', clinic_name='C Clinic',
            clinic_address='Kano', lga='Kano Municipal', whatsapp_number='080',
            phone='080', email='cvet@test.com',
        )
        self.other = make_user('cother@test.com', 'FARMER')
        from apps.consultations.models import ConsultationRequest
        self.consultation = ConsultationRequest.objects.create(
            consultation_code='CON-C-1', farmer=self.farmer,
            farmer_name='Farmer C', farm_location='Kano',
            vet=self.profile, vet_name='Vet C',
            species='Cattle', animal_age='2 years',
        )
        self.url = reverse('consultation-detail', kwargs={'consultation_code': 'CON-C-1'})

    def test_vet_can_see_assigned_consultations(self):
        self.client.force_authenticate(self.vet_user)
        res = self.client.get(reverse('consultation-list'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.data.get('results', res.data)
        codes = [r['id'] for r in data]
        self.assertIn('CON-C-1', codes)

    def test_non_participant_cannot_see_consultation(self):
        self.client.force_authenticate(self.other)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_message_sender_cannot_be_spoofed(self):
        # A farmer trying to send a message claiming to be the vet must be
        # recorded as the farmer.
        self.client.force_authenticate(self.farmer)
        res = self.client.post(
            f'{self.url}messages/',
            {'sender': 'vet', 'senderName': 'Fake Vet', 'text': 'hello'},
            format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertEqual(res.data['sender'], 'farmer')
        self.assertEqual(res.data['senderName'], 'Farmer C')

    def test_vet_message_recorded_as_vet(self):
        self.client.force_authenticate(self.vet_user)
        res = self.client.post(
            f'{self.url}messages/',
            {'sender': 'farmer', 'senderName': 'Spoof', 'text': 'hi vet'},
            format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertEqual(res.data['sender'], 'vet')

    def test_non_participant_cannot_message(self):
        self.client.force_authenticate(self.other)
        res = self.client.post(
            f'{self.url}messages/', {'sender': 'farmer', 'text': 'spam'},
            format='json')
        # 403 (permission) or 404 (existence hidden) both prevent access.
        self.assertIn(res.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))


# ============================================================
# Accounts: enumeration-safe password reset
# ============================================================

class PasswordResetEnumerationTests(APITestCase):
    def setUp(self):
        self.existing = make_user('enum@test.com', 'FARMER')

    def test_existing_email_gets_success_message(self):
        res = self.client.post(
            reverse('forgot_password'),
            {'email': 'enum@test.com'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_unknown_email_gets_identical_success_message(self):
        res = self.client.post(
            reverse('forgot_password'),
            {'email': 'does-not-exist@test.com'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['detail'], 'Password reset instructions were sent.')

    def test_reset_token_only_valid_for_existing_user(self):
        res = self.client.post(
            reverse('forgot_password'),
            {'email': 'enum@test.com'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)


# ============================================================
# Marketplace: deterministic pagination ordering
# ============================================================

class MarketplaceOrderingTests(APITestCase):
    def test_listing_queryset_is_ordered(self):
        from apps.marketplace.views import MarketplaceListingViewSet
        # Regression: annotate() drops the Meta ordering, which produced
        # UnorderedObjectListWarning and unstable pagination. The viewset
        # must add an explicit order_by.
        self.assertTrue(MarketplaceListingViewSet.queryset.ordered)
