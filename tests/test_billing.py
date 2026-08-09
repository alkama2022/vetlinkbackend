from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.billing.models import Invoice as BillingInvoice
from apps.payments.models import Invoice as PaymentInvoice
from apps.payments.models import Payment


User = get_user_model()


def make_user(email, user_type):
    return User.objects.create_user(
        email=email,
        password='StrongPass123!',
        full_name=email.split('@')[0].replace('.', ' ').title(),
        user_type=user_type,
        is_email_verified=True,
    )


class BillingInvoiceTests(APITestCase):
    def setUp(self):
        self.staff = make_user('clinic@example.com', 'CLINIC_ADMIN')
        self.farmer = make_user('farmer@example.com', 'FARMER')
        self.invoice = BillingInvoice.objects.create(
            invoice_code='INV-TEST-001',
            owner_name='Ibrahim Musa',
            animal='Bull (cattle)',
            total='25000.00',
            status='Unpaid',
        )

    def test_invoice_id_is_exposed_as_code(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.get('/api/v1/invoices/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'][0]['id'], 'INV-TEST-001')

    def test_mark_paid_works_with_invoice_code(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.post('/api/v1/invoices/INV-TEST-001/pay/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, 'Paid')

    def test_checkout_creates_payment_and_returns_reference(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.post(
            '/api/v1/invoices/INV-TEST-001/checkout/',
            {'redirect_url': 'https://app.example/payments'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('checkout_url', response.data)
        self.assertIn('payment_id', response.data)
        self.assertTrue(response.data['reference'])

        payment = Payment.objects.get(id=response.data['payment_id'])
        self.assertEqual(payment.invoice.invoice_number, 'INV-TEST-001')
        self.assertEqual(str(payment.amount), '25000.00')

    def test_checkout_reuses_payments_invoice(self):
        self.client.force_authenticate(user=self.staff)
        first = self.client.post('/api/v1/invoices/INV-TEST-001/checkout/', {}, format='json')
        second = self.client.post('/api/v1/invoices/INV-TEST-001/checkout/', {}, format='json')
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(PaymentInvoice.objects.filter(invoice_number='INV-TEST-001').count(), 1)

    def test_checkout_rejects_paid_invoice(self):
        self.invoice.status = 'Paid'
        self.invoice.save(update_fields=['status'])
        self.client.force_authenticate(user=self.staff)
        response = self.client.post('/api/v1/invoices/INV-TEST-001/checkout/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_checkout_requires_clinic_staff(self):
        self.client.force_authenticate(user=self.farmer)
        response = self.client.post('/api/v1/invoices/INV-TEST-001/checkout/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_webhook_marks_billing_invoice_paid(self):
        self.client.force_authenticate(user=self.staff)
        checkout = self.client.post('/api/v1/invoices/INV-TEST-001/checkout/', {}, format='json')
        reference = checkout.data['reference']

        response = self.client.post(
            '/api/v1/payments/webhook/',
            {'reference': reference},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, 'Paid')
        payment = Payment.objects.get(id=checkout.data['payment_id'])
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'successful')
