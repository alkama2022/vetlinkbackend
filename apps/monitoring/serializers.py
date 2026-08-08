from rest_framework import serializers

from apps.monitoring.models import (
    Alert,
    ErrorLog,
    Incident,
    IncidentRCA,
    IncidentUpdate,
    SystemEvent,
)


class ErrorLogSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True, default=None)
    incident_id = serializers.CharField(source='incident.incident_id', read_only=True, default=None)
    error_id = serializers.CharField(read_only=True)
    timestamp = serializers.DateTimeField(read_only=True)

    class Meta:
        model = ErrorLog
        fields = [
            'id', 'error_id', 'timestamp', 'severity', 'category', 'source',
            'module', 'endpoint', 'method', 'status_code', 'user', 'user_email',
            'user_role', 'correlation_id', 'exception_type', 'message',
            'stack_trace', 'environment', 'duration_ms', 'resolution_status',
            'incident', 'incident_id', 'archived', 'metadata',
        ]
        read_only_fields = [
            'id', 'error_id', 'timestamp', 'user', 'user_email', 'user_role',
            'environment', 'incident', 'incident_id',
        ]


class ErrorLogCreateSerializer(serializers.ModelSerializer):
    """Ingestion payload — used by frontend error reporting and tests.

    The user is always taken from the authenticated request; frontends cannot
    spoof identity.
    """

    class Meta:
        model = ErrorLog
        fields = [
            'severity', 'category', 'source', 'module', 'endpoint', 'method',
            'status_code', 'correlation_id', 'exception_type', 'message',
            'stack_trace', 'duration_ms', 'metadata',
        ]

    def validate(self, attrs):
        attrs['message'] = (attrs.get('message') or '').strip()
        if not attrs['message']:
            raise serializers.ValidationError({'message': 'message is required'})
        if len(attrs['message']) > 4000:
            attrs['message'] = attrs['message'][:4000]
        return attrs


class IncidentUpdateSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.full_name', read_only=True, default='')

    class Meta:
        model = IncidentUpdate
        fields = ['id', 'incident', 'author', 'author_name', 'status', 'note', 'created_at']
        read_only_fields = ['id', 'author', 'author_name', 'created_at']


class IncidentRcaSerializer(serializers.ModelSerializer):
    documented_by_name = serializers.CharField(source='documented_by.full_name',
                                               read_only=True, default='')

    class Meta:
        model = IncidentRCA
        fields = [
            'id', 'incident', 'root_cause', 'impact', 'fix', 'preventive_action',
            'related_deployment', 'related_commit', 'lessons_learned',
            'documented_by', 'documented_by_name', 'documented_at',
        ]
        read_only_fields = ['id', 'incident', 'documented_by', 'documented_by_name',
                            'documented_at']


class IncidentSerializer(serializers.ModelSerializer):
    incident_id = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    resolved_at = serializers.DateTimeField(read_only=True)
    assigned_engineer_name = serializers.CharField(
        source='assigned_engineer.full_name', read_only=True, default='')
    created_by_name = serializers.CharField(source='created_by.full_name',
                                            read_only=True, default='')
    log_count = serializers.IntegerField(source='logs.count', read_only=True)
    updates = IncidentUpdateSerializer(many=True, read_only=True)
    rca = IncidentRcaSerializer(read_only=True)

    class Meta:
        model = Incident
        fields = [
            'id', 'incident_id', 'title', 'description', 'severity', 'status',
            'source', 'module', 'assigned_engineer', 'assigned_engineer_name',
            'created_by', 'created_by_name', 'resolution_notes',
            'created_at', 'updated_at', 'resolved_at', 'log_count',
            'updates', 'rca',
        ]
        read_only_fields = ['id', 'incident_id', 'created_at', 'updated_at',
                            'resolved_at', 'created_by', 'log_count', 'updates', 'rca']


class SystemEventSerializer(serializers.ModelSerializer):
    actor_email = serializers.CharField(source='actor.email', read_only=True, default=None)
    event_id = serializers.CharField(read_only=True)
    timestamp = serializers.DateTimeField(read_only=True)

    class Meta:
        model = SystemEvent
        fields = [
            'id', 'event_id', 'category', 'action', 'actor', 'actor_email',
            'actor_role', 'target_type', 'target_id', 'details', 'ip_address',
            'correlation_id', 'timestamp',
        ]
        read_only_fields = fields


class AlertSerializer(serializers.ModelSerializer):
    alert_id = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Alert
        fields = [
            'id', 'alert_id', 'title', 'message', 'severity', 'category',
            'module', 'correlation_id', 'error', 'channels',
            'created_at', 'acknowledged_at',
        ]
        read_only_fields = fields
