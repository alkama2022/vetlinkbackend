import os
import requests
from abc import ABC, abstractmethod
from django.conf import settings


class BaseGateway(ABC):
    @abstractmethod
    def initialize_payment(self, amount, currency, metadata, idempotency_key=None):
        pass

    @abstractmethod
    def verify_webhook(self, request):
        pass

    @abstractmethod
    def verify_transaction(self, transaction_id):
        pass


class FlutterwaveGateway(BaseGateway):
    VERIFY_HEADER = 'verif-hash'

    def __init__(self, secret_key=None, public_key=None, base_url=None, webhook_secret=None):
        self.secret_key = secret_key or getattr(settings, 'FLUTTERWAVE_SECRET_KEY', '') or os.getenv('FLUTTERWAVE_SECRET_KEY', '')
        self.public_key = public_key or getattr(settings, 'FLUTTERWAVE_PUBLIC_KEY', '') or os.getenv('FLUTTERWAVE_PUBLIC_KEY', '')
        self.base_url = base_url or getattr(settings, 'FLUTTERWAVE_API_BASE', 'https://api.flutterwave.com/v3') or os.getenv('FLUTTERWAVE_API_BASE', 'https://api.flutterwave.com/v3')
        self.webhook_secret = webhook_secret or getattr(settings, 'FLUTTERWAVE_WEBHOOK_SECRET', '') or os.getenv('FLUTTERWAVE_WEBHOOK_SECRET', self.secret_key)

    def _headers(self, idempotency_key=None):
        headers = {
            'Authorization': f'Bearer {self.secret_key}',
            'Content-Type': 'application/json'
        }
        if idempotency_key:
            headers['Idempotency-Key'] = idempotency_key
        return headers

    def initialize_payment(self, amount, currency='NGN', metadata=None, idempotency_key=None):
        metadata = metadata or {}
        payload = {
            'tx_ref': metadata.get('tx_ref'),
            'amount': str(amount),
            'currency': currency,
            'redirect_url': metadata.get('redirect_url', ''),
            'customer': {
                'email': metadata.get('customer_email', ''),
                'name': metadata.get('customer_name', ''),
            },
            'customizations': {
                'title': metadata.get('title', 'VetLink Payment'),
                'description': metadata.get('description', 'Payment for veterinary services'),
            },
            'meta': metadata,
        }
        response = requests.post(
            f'{self.base_url}/payments',
            json=payload,
            headers=self._headers(idempotency_key),
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        if data.get('status') != 'success' or 'data' not in data:
            raise ValueError('Flutterwave payment initialization failed')
        checkout_url = data['data'].get('link') or data['data'].get('authorization_url')
        return {
            'checkout_url': checkout_url,
            'reference': data['data'].get('id'),
            'transaction_id': data['data'].get('id'),
            'payload': data['data'],
        }

    def verify_webhook(self, request):
        signature = request.headers.get(self.VERIFY_HEADER)
        return bool(signature and self.webhook_secret and signature == self.webhook_secret)

    def verify_transaction(self, transaction_id):
        response = requests.get(
            f'{self.base_url}/transactions/{transaction_id}/verify',
            headers=self._headers(),
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        if data.get('status') == 'success' and data.get('data', {}).get('status') == 'successful':
            return data['data']
        raise ValueError('Transaction verification failed')


class StubGateway(BaseGateway):
    """Simple stubbed gateway for local/dev testing. Replace with real provider integrations."""

    def initialize_payment(self, amount, currency='NGN', metadata=None, idempotency_key=None):
        return {
            'checkout_url': 'https://stub.pay/checkout',
            'reference': 'STUB-' + (idempotency_key or 'ref'),
            'transaction_id': 'STUB-' + (idempotency_key or 'ref'),
            'payload': metadata or {},
        }

    def verify_webhook(self, request):
        return True

    def verify_transaction(self, transaction_id):
        return {'status': 'successful', 'id': transaction_id}


def get_gateway_provider(gateway=None):
    if gateway and gateway.provider == 'flutterwave':
        config = gateway.config or {}
        return FlutterwaveGateway(
            secret_key=config.get('secret_key'),
            public_key=config.get('public_key'),
            base_url=config.get('api_base'),
            webhook_secret=config.get('webhook_secret'),
        )
    return StubGateway()
