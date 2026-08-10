"""API endpoints for the monitoring system.

Security model:
  * Frontend ingestion (`POST /monitoring/errors/`) — any authenticated user.
  * Everything else (read/search/update, incidents, events, dashboard) —
    administrators/engineers only (IsMonitoringAdmin).
  * `POST /monitoring/test-failure/` — development environments only.
"""

from datetime import datetime, timedelta

from django.conf import settings
from django.db.models import Count, Q
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.monitoring.models import (
    Alert,
    ErrorLog,
    Incident,
    IncidentRCA,
    IncidentStatus,
    IncidentUpdate,
    LogCategory,
    LogSeverity,
    LogSource,
    SystemEvent,
)
from apps.monitoring.permissions import IsMonitoringAdmin
from apps.monitoring.serializers import (
    AlertSerializer,
    ErrorLogCreateSerializer,
    ErrorLogSerializer,
    IncidentRcaSerializer,
    IncidentSerializer,
    IncidentUpdateSerializer,
    SystemEventSerializer,
)
from apps.monitoring.services import capture_error, record_event, sanitize_dict


class MonitoringPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


class ErrorLogViewSet(viewsets.ModelViewSet):
    """Central error log. POST is open to any authenticated user (ingestion);
    read/update operations are admin-only."""

    queryset = ErrorLog.objects.select_related('user', 'incident')
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['severity', 'category', 'source', 'status_code',
                        'resolution_status', 'environment', 'method']
    search_fields = ['error_id', 'message', 'module', 'endpoint',
                     'exception_type', 'correlation_id', 'user__email']
    ordering_fields = ['timestamp', 'severity', 'duration_ms']
    ordering = ['-timestamp']
    pagination_class = MonitoringPagination

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated()]
        return [IsMonitoringAdmin()]

    def get_serializer_class(self):
        if self.action == 'create':
            return ErrorLogCreateSerializer
        return ErrorLogSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        # Filtering helpers not expressible as filterset_fields.
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            try:
                parsed = timezone.make_aware(
                    datetime.strptime(date_from, '%Y-%m-%d'))
            except ValueError:
                raise ValidationError({'date_from': 'Invalid date format, expected YYYY-MM-DD.'})
            qs = qs.filter(timestamp__gte=parsed)
        if date_to:
            qs = qs.filter(timestamp__date__lte=date_to)
        return qs

    def perform_create(self, serializer):
        request = self.request
        source = serializer.validated_data.get('source', LogSource.FRONTEND)
        if request.headers.get('X-Source', '').lower() == 'frontend':
            source = LogSource.FRONTEND
        serializer.save(
            source=source,
            user=request.user if request.user.is_authenticated else None,
            user_role=getattr(request.user, 'user_type', '') if request.user.is_authenticated else '',
            environment=getattr(settings, 'ENVIRONMENT', 'development'),
            correlation_id=serializer.validated_data.get('correlation_id')
            or getattr(request, 'correlation_id', ''),
            ip_address=_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:512],
            metadata=sanitize_dict(serializer.validated_data.get('metadata') or {}),
        )

    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        log = self.get_object()
        log.resolution_status = 'ACKNOWLEDGED'
        log.acknowledged_by = request.user
        log.acknowledged_at = timezone.now()
        log.save(update_fields=['resolution_status', 'acknowledged_by', 'acknowledged_at'])
        return Response(ErrorLogSerializer(log).data)

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        log = self.get_object()
        log.resolution_status = 'RESOLVED'
        log.resolved_by = request.user
        log.resolved_at = timezone.now()
        log.save(update_fields=['resolution_status', 'resolved_by', 'resolved_at'])
        record_event(
            category='ADMIN', action='error.resolved', actor=request.user,
            target_type='error', target_id=log.error_id,
            request=request, details={'severity': log.severity, 'module': log.module},
        )
        return Response(ErrorLogSerializer(log).data)

    @action(detail=True, methods=['post'])
    def link_incident(self, request, pk=None):
        log = self.get_object()
        incident = Incident.objects.filter(incident_id=request.data.get('incident_id', '')).first()
        if not incident:
            return Response({'detail': 'Incident not found'}, status=status.HTTP_404_NOT_FOUND)
        log.incident = incident
        log.resolution_status = 'INVESTIGATING'
        log.save(update_fields=['incident', 'resolution_status'])
        return Response(ErrorLogSerializer(log).data)


class IncidentViewSet(viewsets.ModelViewSet):
    queryset = Incident.objects.select_related('assigned_engineer', 'created_by').prefetch_related(
        'updates', 'logs')
    serializer_class = IncidentSerializer
    permission_classes = [IsMonitoringAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'severity', 'source', 'module']
    search_fields = ['incident_id', 'title', 'description', 'module', 'assigned_engineer__email']
    ordering_fields = ['created_at', 'updated_at', 'severity', 'status']
    ordering = ['-created_at']
    pagination_class = MonitoringPagination

    def perform_create(self, serializer):
        incident = serializer.save(created_by=self.request.user)
        record_event(
            category='ADMIN', action='incident.created', actor=self.request.user,
            target_type='incident', target_id=incident.incident_id,
            request=self.request,
            details={'title': incident.title, 'severity': incident.severity},
        )
        error_ids = self.request.data.get('error_ids') or []
        if isinstance(error_ids, list):
            ErrorLog.objects.filter(id__in=error_ids).update(
                incident=incident, resolution_status='INVESTIGATING')

    def perform_update(self, serializer):
        incident = serializer.save()
        record_event(
            category='ADMIN', action='incident.updated', actor=self.request.user,
            target_type='incident', target_id=incident.incident_id,
            request=self.request,
            details={'status': incident.status, 'severity': incident.severity},
        )

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        incident = self.get_object()
        engineer = request.data.get('engineer_id')
        if engineer:
            from django.contrib.auth import get_user_model
            try:
                incident.assigned_engineer = get_user_model().objects.get(pk=engineer)
            except get_user_model().DoesNotExist:
                return Response({'detail': 'Engineer not found'},
                                status=status.HTTP_404_NOT_FOUND)
        else:
            incident.assigned_engineer = None
        incident.save(update_fields=['assigned_engineer', 'updated_at'])
        return Response(IncidentSerializer(incident).data)

    @action(detail=True, methods=['post'])
    def add_update(self, request, pk=None):
        incident = self.get_object()
        note = (request.data.get('note') or '').strip()
        if not note:
            return Response({'detail': 'note is required'}, status=status.HTTP_400_BAD_REQUEST)
        requested_status = request.data.get('status', incident.status)
        if requested_status not in IncidentStatus.values:
            return Response({'detail': 'invalid status'}, status=status.HTTP_400_BAD_REQUEST)
        update = IncidentUpdate.objects.create(
            incident=incident,
            author=request.user,
            status=requested_status,
            note=note[:4000],
        )
        if requested_status != incident.status:
            incident.status = requested_status
            incident.save(update_fields=['status', 'updated_at', 'resolved_at'])
        return Response(IncidentUpdateSerializer(update).data,
                        status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get', 'post', 'patch'])
    def rca(self, request, pk=None):
        incident = self.get_object()
        rca, created = IncidentRCA.objects.get_or_create(incident=incident)
        if request.method == 'GET':
            return Response(IncidentRcaSerializer(rca).data)
        data = request.data
        serializer = IncidentRcaSerializer(rca, data=data, partial=request.method == 'PATCH')
        serializer.is_valid(raise_exception=True)
        serializer.instance.documented_by = request.user
        serializer.save()
        return Response(IncidentRcaSerializer(rca).data,
                        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class SystemEventViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SystemEvent.objects.select_related('actor')
    serializer_class = SystemEventSerializer
    permission_classes = [IsMonitoringAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'action']
    search_fields = ['event_id', 'action', 'actor__email', 'target_id', 'details']
    ordering_fields = ['timestamp']
    ordering = ['-timestamp']
    pagination_class = MonitoringPagination

    def get_queryset(self):
        qs = super().get_queryset()
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            qs = qs.filter(timestamp__gte=date_from)
        if date_to:
            qs = qs.filter(timestamp__date__lte=date_to)
        return qs


class AlertViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Alert.objects.select_related('error')
    serializer_class = AlertSerializer
    permission_classes = [IsMonitoringAdmin]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['severity', 'category', 'module']
    ordering = ['-created_at']
    pagination_class = MonitoringPagination


class MonitoringDashboardView(APIView):
    """Aggregated KPIs for the admin monitoring page."""

    permission_classes = [IsMonitoringAdmin]

    def get(self, request):
        now = timezone.now()
        today = now - timedelta(days=1)

        def count(**filters):
            return ErrorLog.objects.filter(**filters).count()

        recent_errors = ErrorLog.objects.select_related('user')[:10]
        recent_incidents = Incident.objects.select_related('assigned_engineer')[:5]
        recent_events = SystemEvent.objects.select_related('actor')[:10]

        return Response({
            'summary': {
                'total_errors': ErrorLog.objects.count(),
                'errors_today': count(timestamp__gte=today),
                'critical_errors': count(severity=LogSeverity.CRITICAL),
                'open_incidents': Incident.objects.exclude(
                    status__in=[IncidentStatus.RESOLVED, IncidentStatus.CLOSED]).count(),
                'api_failures_today': count(category=LogCategory.API, timestamp__gte=today),
                'auth_failures_today': count(category=LogCategory.AUTH, timestamp__gte=today),
                'db_errors': count(category=LogCategory.DB),
                'ai_failures': count(category=LogCategory.AI),
                'payment_failures': count(category=LogCategory.PAYMENT),
                'performance_warnings_today': count(
                    category=LogCategory.PERFORMANCE, timestamp__gte=today),
                'security_events_today': count(category=LogCategory.SECURITY,
                                               timestamp__gte=today),
                'alerts_active': Alert.objects.filter(acknowledged_at__isnull=True).count(),
            },
            'by_severity': list(
                ErrorLog.objects.values('severity')
                .annotate(count=Count('id')).order_by('-count')),
            'by_category': list(
                ErrorLog.objects.values('category')
                .annotate(count=Count('id')).order_by('-count')[:12]),
            'recent_errors': ErrorLogSerializer(recent_errors, many=True).data,
            'recent_incidents': IncidentSerializer(recent_incidents, many=True).data,
            'recent_events': SystemEventSerializer(recent_events, many=True).data,
        })


class TestFailureView(APIView):
    """Intentional failure generator for development/staging verification.

    Returns 403 unless settings.MONITORING_ALLOW_TEST_FAILURES is true
    (defaults to DEBUG). Never callable in production.
    """

    permission_classes = [IsAuthenticated]

    def _allowed(self) -> bool:
        allowed = getattr(settings, 'MONITORING_SETTINGS', {}).get('ALLOW_TEST_FAILURES')
        if allowed is None:
            allowed = settings.DEBUG
        return bool(allowed)

    def post(self, request):
        if not self._allowed():
            return Response({'detail': 'Test failures are disabled in this environment'},
                            status=status.HTTP_403_FORBIDDEN)
        kind = request.data.get('kind', 'api_error')
        if kind == 'crash':
            raise RuntimeError('Intentional test crash for monitoring verification')
        if kind == 'frontend_error':
            log = capture_error(
                message=request.data.get('message', 'Intentional frontend test error'),
                severity=LogSeverity.ERROR,
                category=LogCategory.REACT,
                module=request.data.get('module', 'frontend.test'),
                source=LogSource.FRONTEND,
                request=request,
                status_code=500,
                metadata={'test': True},
            )
        elif kind == 'critical':
            log = capture_error(
                message=request.data.get('message', 'Intentional critical test error'),
                severity=LogSeverity.CRITICAL,
                category=LogCategory.SYSTEM,
                module=request.data.get('module', 'monitoring.test'),
                source=LogSource.BACKEND,
                request=request,
                status_code=500,
                metadata={'test': True},
            )
        else:
            try:
                raise ValueError(request.data.get('message', 'Intentional test exception'))
            except ValueError as exc:
                log = capture_error(
                    message=str(exc), severity=LogSeverity.ERROR,
                    category=LogCategory.API, module='monitoring.test',
                    source=LogSource.BACKEND, request=request, exc=exc,
                    status_code=500, metadata={'test': True},
                )
        if log:
            from apps.monitoring.alerting import fire_alert
            fire_alert(
                title=f'[TEST] {log.error_id}',
                message=log.message, severity=log.severity,
                category=log.category, module=log.module,
                correlation_id=log.correlation_id, error=log,
            )
        return Response({'detail': 'Test failure logged', 'error_id': log.error_id},
                        status=status.HTTP_201_CREATED)


def _client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')
