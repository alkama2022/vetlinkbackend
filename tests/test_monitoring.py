"""Monitoring system tests.

Covers the verification checklist:
  * backend exception creates log
  * frontend exception is captured (ingestion)
  * API failure recorded
  * authentication failure recorded
  * incident lifecycle (create -> investigate -> resolve -> RCA)
  * admin can view logs; normal users cannot
  * sensitive information is never logged
  * pagination + filtering
  * correlation IDs
  * audit events on register/login
  * health endpoints
"""

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.monitoring.models import (
    ErrorLog,
    Incident,
    IncidentRCA,
    IncidentStatus,
    SystemEvent,
)

User = get_user_model()

TEST_MONITORING = {
    'ALLOW_TEST_FAILURES': True,
    'API_SLOW_WARNING_MS': 2000,
    'API_SLOW_ERROR_MS': 5000,
}


@override_settings(MONITORING_SETTINGS=TEST_MONITORING, SECURE_SSL_REDIRECT=False,
                   ENVIRONMENT='development')
class MonitoringBaseTestCase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email='admin@example.com', password='Password123!',
            full_name='Admin User', user_type='SYSTEM_ADMIN',
            is_email_verified=True)
        self.superuser = User.objects.create_superuser(
            email='super@example.com', password='SuperPass123!',
            full_name='Super User')
        self.farmer = User.objects.create_user(
            email='farmer@example.com', password='Password123!',
            full_name='Farmer User', user_type='FARMER',
            is_email_verified=True)

    def _auth_client(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    def _ingest_error(self, client=None, **overrides):
        client = client or self._auth_client(self.farmer)
        payload = {
            'severity': 'ERROR',
            'category': 'REACT',
            'source': 'FRONTEND',
            'module': 'frontend.test',
            'endpoint': '/dashboard',
            'method': 'GET',
            'message': 'Cannot read properties of undefined',
            'stack_trace': 'Error: boom\n  at Home (dashboard.tsx:42)',
            'correlation_id': 'WEB-TEST-123',
            'status_code': 500,
            **overrides,
        }
        return client.post('/api/v1/monitoring/errors/', payload, format='json')


class ErrorCaptureTests(MonitoringBaseTestCase):
    def test_frontend_ingestion_creates_log(self):
        response = self._ingest_error()
        self.assertEqual(response.status_code, 201)
        log = ErrorLog.objects.get(correlation_id='WEB-TEST-123')
        self.assertEqual(log.source, 'FRONTEND')
        self.assertEqual(log.category, 'REACT')
        self.assertEqual(log.user, self.farmer)
        self.assertEqual(log.user_role, 'FARMER')
        self.assertEqual(log.environment, 'development')

    def test_ingestion_requires_auth(self):
        response = APIClient().post('/api/v1/monitoring/errors/', {'message': 'x'},
                                    format='json')
        self.assertEqual(response.status_code, 401)

    def test_ingestion_rejects_empty_message(self):
        response = self._ingest_error(message='   ')
        self.assertEqual(response.status_code, 400)

    def test_secrets_are_redacted(self):
        self._ingest_error(metadata={'password': 'hunter2', 'token': 'abc',
                                     'safe': {'nested_secret': 'zzz', 'ok': 1}})
        log = ErrorLog.objects.latest('id')
        self.assertEqual(log.metadata['password'], '[REDACTED]')
        self.assertEqual(log.metadata['token'], '[REDACTED]')
        self.assertEqual(log.metadata['safe']['nested_secret'], '[REDACTED]')
        self.assertEqual(log.metadata['safe']['ok'], 1)

    def test_backend_exception_creates_log(self):
        client = self._auth_client(self.farmer)
        client.raise_request_exception = False
        response = client.post('/api/v1/monitoring/test-failure/', {'kind': 'crash'},
                               format='json')
        self.assertEqual(response.status_code, 500)
        log = ErrorLog.objects.filter(severity='ERROR', status_code=500).latest('id')
        self.assertEqual(log.module, 'monitoring_test_failure')
        self.assertIn('Intentional test crash', log.message)

    def test_test_failure_endpoint_disabled_in_production(self):
        with override_settings(MONITORING_SETTINGS={**TEST_MONITORING,
                                                     'ALLOW_TEST_FAILURES': False}):
            client = self._auth_client(self.farmer)
            response = client.post('/api/v1/monitoring/test-failure/',
                                   {'kind': 'api_error'}, format='json')
            self.assertEqual(response.status_code, 403)

    def test_authentication_failure_is_logged(self):
        client = APIClient()
        response = client.post('/api/v1/auth/token/',
                               {'email': 'nobody@example.com', 'password': 'wrong'},
                               format='json')
        self.assertEqual(response.status_code, 401)
        log = ErrorLog.objects.filter(category='AUTH').latest('id')
        self.assertEqual(log.severity, 'WARNING')
        self.assertEqual(log.metadata['email'], 'nobody@example.com')
        self.assertNotIn('wrong', log.message)
        self.assertTrue(SystemEvent.objects.filter(action='auth.login_failed').exists())


class AccessControlTests(MonitoringBaseTestCase):
    def test_normal_user_cannot_list_logs(self):
        self._ingest_error()
        response = self._auth_client(self.farmer).get('/api/v1/monitoring/errors/')
        self.assertEqual(response.status_code, 403)

    def test_admin_can_list_and_view_logs(self):
        self._ingest_error()
        client = self._auth_client(self.admin)
        response = client.get('/api/v1/monitoring/errors/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        detail = client.get(
            f"/api/v1/monitoring/errors/{response.data['results'][0]['id']}/")
        self.assertEqual(detail.status_code, 200)

    def test_normal_user_cannot_view_incidents(self):
        response = self._auth_client(self.farmer).get('/api/v1/monitoring/incidents/')
        self.assertEqual(response.status_code, 403)

    def test_superuser_can_access_everything(self):
        self._ingest_error()
        client = self._auth_client(self.superuser)
        self.assertEqual(client.get('/api/v1/monitoring/errors/').status_code, 200)
        self.assertEqual(client.get('/api/v1/monitoring/dashboard/').status_code, 200)


class PaginationAndFilteringTests(MonitoringBaseTestCase):
    def test_pagination(self):
        client = self._auth_client(self.farmer)
        for i in range(30):
            self._ingest_error(client, message=f'boom {i}')
        response = self._auth_client(self.admin).get('/api/v1/monitoring/errors/')
        self.assertEqual(response.data['count'], 30)
        self.assertEqual(len(response.data['results']), 25)
        page2 = self._auth_client(self.admin).get(
            '/api/v1/monitoring/errors/', {'page': 2})
        self.assertEqual(len(page2.data['results']), 5)

    def test_severity_filter(self):
        client = self._auth_client(self.farmer)
        self._ingest_error(client, severity='ERROR', message='e1')
        self._ingest_error(client, severity='CRITICAL', message='e2')
        response = self._auth_client(self.admin).get(
            '/api/v1/monitoring/errors/', {'severity': 'CRITICAL'})
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['message'], 'e2')

    def test_search_by_error_id(self):
        self._ingest_error(message='unique search target')
        log = ErrorLog.objects.latest('id')
        response = self._auth_client(self.admin).get(
            '/api/v1/monitoring/errors/', {'search': log.error_id})
        self.assertEqual(response.data['count'], 1)

    def test_date_range_filter(self):
        client = self._auth_client(self.farmer)
        self._ingest_error(client, message='recent')
        self._ingest_error(client, message='ancient')
        ancient = ErrorLog.objects.filter(message='ancient').latest('id')
        ErrorLog.objects.filter(pk=ancient.pk).update(timestamp='2020-01-01T00:00:00Z')
        response = self._auth_client(self.admin).get(
            '/api/v1/monitoring/errors/', {'date_from': '2021-01-01'})
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['message'], 'recent')


class CorrelationIdTests(MonitoringBaseTestCase):
    def test_ingested_correlation_id_preserved(self):
        self._ingest_error(correlation_id='CORR-ABC-123')
        log = ErrorLog.objects.latest('id')
        self.assertEqual(log.correlation_id, 'CORR-ABC-123')

    def test_backend_generates_correlation_id_on_response(self):
        response = APIClient().get('/api/v1/health/live/')
        self.assertIn('X-Correlation-ID', response)
        self.assertTrue(response['X-Correlation-ID'])

    def test_upstream_correlation_id_respected(self):
        client = APIClient()
        response = client.get('/api/v1/health/live/',
                              HTTP_X_CORRELATION_ID='UPSTREAM-42')
        self.assertEqual(response['X-Correlation-ID'], 'UPSTREAM-42')


class IncidentTests(MonitoringBaseTestCase):
    def test_incident_lifecycle_and_rca(self):
        client = self._auth_client(self.admin)
        # Create incident linked to a logged error
        self._ingest_error(message='payment gateway down')
        log = ErrorLog.objects.latest('id')
        create = client.post('/api/v1/monitoring/incidents/', {
            'title': 'Payments failing',
            'description': 'Gateway 500s',
            'severity': 'CRITICAL',
            'status': 'OPEN',
            'module': 'payments',
            'error_ids': [log.id],
        }, format='json')
        self.assertEqual(create.status_code, 201)
        incident = Incident.objects.get()
        self.assertEqual(incident.status, IncidentStatus.OPEN)
        log.refresh_from_db()
        self.assertEqual(log.incident, incident)
        self.assertEqual(log.resolution_status, 'INVESTIGATING')

        # Add an investigation update + transition status
        update = client.post(f'/api/v1/monitoring/incidents/{incident.id}/add_update/', {
            'note': 'Gateway provider unresponsive',
            'status': 'IN_PROGRESS',
        }, format='json')
        self.assertEqual(update.status_code, 201)
        incident.refresh_from_db()
        self.assertEqual(incident.status, 'IN_PROGRESS')

        # Resolve via update
        client.post(f'/api/v1/monitoring/incidents/{incident.id}/add_update/', {
            'note': 'Fixed by switching provider',
            'status': 'RESOLVED',
        }, format='json')
        incident.refresh_from_db()
        self.assertEqual(incident.status, 'RESOLVED')
        self.assertIsNotNone(incident.resolved_at)

        # RCA documentation
        rca = client.post(f'/api/v1/monitoring/incidents/{incident.id}/rca/', {
            'root_cause': 'Flaky upstream gateway',
            'impact': 'Payments blocked for 1h',
            'fix': 'Provider failover',
            'preventive_action': 'Add circuit breaker',
            'related_commit': 'a1b2c3',
            'lessons_learned': 'Monitor gateway latency',
        }, format='json')
        self.assertEqual(rca.status_code, 201)
        self.assertTrue(IncidentRCA.objects.filter(incident=incident).exists())

    def test_incident_resolution_notes(self):
        client = self._auth_client(self.admin)
        response = client.post('/api/v1/monitoring/incidents/', {
            'title': 'Database timeouts',
            'status': 'OPEN',
            'severity': 'HIGH',
            'resolution_notes': 'Tuned connection pool',
        }, format='json')
        self.assertEqual(response.status_code, 201)

    def test_error_link_incident_and_resolve(self):
        client = self._auth_client(self.admin)
        self._ingest_error(message='need linking')
        log = ErrorLog.objects.latest('id')
        incident = Incident.objects.create(title='T', created_by=self.admin)
        link = client.post(f'/api/v1/monitoring/errors/{log.id}/link_incident/',
                           {'incident_id': incident.incident_id}, format='json')
        self.assertEqual(link.status_code, 200)
        log.refresh_from_db()
        self.assertEqual(log.incident, incident)
        resolve = client.post(f'/api/v1/monitoring/errors/{log.id}/resolve/', {}, format='json')
        self.assertEqual(resolve.status_code, 200)
        log.refresh_from_db()
        self.assertEqual(log.resolution_status, 'RESOLVED')
        self.assertTrue(SystemEvent.objects.filter(action='error.resolved').exists())


class AuditEventTests(MonitoringBaseTestCase):
    def test_registration_records_event(self):
        response = APIClient().post('/api/v1/auth/register/', {
            'email': 'new@example.com',
            'password': 'Password123!',
            'full_name': 'New Person',
            'user_type': 'FARMER',
            'lga': 'Kano Municipal',
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertTrue(SystemEvent.objects.filter(action='account.registered').exists())

    def test_successful_login_records_event(self):
        user = User.objects.create_user(
            email='login@example.com', password='Password123!',
            full_name='Login User', user_type='FARMER',
            is_email_verified=True)
        response = APIClient().post('/api/v1/auth/token/', {
            'email': 'login@example.com', 'password': 'Password123!',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(SystemEvent.objects.filter(action='auth.login',
                                                   actor=user).exists())

    def test_admin_dashboard_aggregates(self):
        client = self._auth_client(self.farmer)
        for _ in range(3):
            self._ingest_error(client, severity='CRITICAL', message='x')
        response = self._auth_client(self.admin).get('/api/v1/monitoring/dashboard/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['summary']['total_errors'], 3)
        self.assertEqual(response.data['summary']['critical_errors'], 3)


class HealthCheckTests(MonitoringBaseTestCase):
    def test_health_endpoints(self):
        for path in ['/health/', '/health/live/', '/health/ready/',
                     '/api/v1/health/live/', '/api/v1/health/ready/']:
            response = APIClient().get(path)
            self.assertEqual(response.status_code, 200, path)
            self.assertIn('status', response.json())
