import secrets

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


def _code(prefix: str) -> str:
    return f"{prefix}-{secrets.token_hex(5).upper()}"


class LogSeverity(models.TextChoices):
    DEBUG = 'DEBUG', 'Debug'
    INFO = 'INFO', 'Info'
    WARNING = 'WARNING', 'Warning'
    ERROR = 'ERROR', 'Error'
    CRITICAL = 'CRITICAL', 'Critical'


class LogCategory(models.TextChoices):
    API = 'API', 'API'
    AUTH = 'AUTH', 'Authentication'
    PERMISSION = 'PERMISSION', 'Permission'
    DB = 'DB', 'Database'
    FILE_UPLOAD = 'FILE_UPLOAD', 'File Upload'
    PAYMENT = 'PAYMENT', 'Payment'
    AI = 'AI', 'AI Service'
    CHAT = 'CHAT', 'Chat'
    WEBSOCKET = 'WEBSOCKET', 'WebSocket'
    PERFORMANCE = 'PERFORMANCE', 'Performance'
    SECURITY = 'SECURITY', 'Security'
    FORMS = 'FORMS', 'Form / Validation'
    REACT = 'REACT', 'Frontend Runtime'
    JS = 'JS', 'Frontend JavaScript'
    TASK = 'TASK', 'Background Task'
    SYSTEM = 'SYSTEM', 'System'


class LogSource(models.TextChoices):
    FRONTEND = 'FRONTEND', 'Frontend'
    BACKEND = 'BACKEND', 'Backend'
    EXTERNAL = 'EXTERNAL', 'External Service'


class LogResolutionStatus(models.TextChoices):
    NEW = 'NEW', 'New'
    ACKNOWLEDGED = 'ACKNOWLEDGED', 'Acknowledged'
    INVESTIGATING = 'INVESTIGATING', 'Investigating'
    RESOLVED = 'RESOLVED', 'Resolved'
    IGNORED = 'IGNORED', 'Ignored'


class IncidentStatus(models.TextChoices):
    OPEN = 'OPEN', 'Open'
    INVESTIGATING = 'INVESTIGATING', 'Investigating'
    IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
    RESOLVED = 'RESOLVED', 'Resolved'
    CLOSED = 'CLOSED', 'Closed'


class IncidentSeverity(models.TextChoices):
    LOW = 'LOW', 'Low'
    MEDIUM = 'MEDIUM', 'Medium'
    HIGH = 'HIGH', 'High'
    CRITICAL = 'CRITICAL', 'Critical'


class EventCategory(models.TextChoices):
    AUTH = 'AUTH', 'Authentication'
    ACCOUNT = 'ACCOUNT', 'Account'
    PATIENT = 'PATIENT', 'Patient'
    APPOINTMENT = 'APPOINTMENT', 'Appointment'
    CONSULTATION = 'CONSULTATION', 'Consultation'
    LAB = 'LAB', 'Laboratory'
    SURVEILLANCE = 'SURVEILLANCE', 'Surveillance'
    BILLING = 'BILLING', 'Billing'
    PAYMENT = 'PAYMENT', 'Payment'
    WITHDRAWAL = 'WITHDRAWAL', 'Withdrawal'
    MARKETPLACE = 'MARKETPLACE', 'Marketplace'
    COMMUNITY = 'COMMUNITY', 'Community'
    CHAT = 'CHAT', 'Chat'
    AI = 'AI', 'AI Service'
    VETERINARIAN = 'VETERINARIAN', 'Veterinarian'
    FARMER = 'FARMER', 'Farmer'
    DRUG = 'DRUG', 'Pharmacy'
    ADMIN = 'ADMIN', 'Administration'
    SECURITY = 'SECURITY', 'Security'
    SYSTEM = 'SYSTEM', 'System'


class Incident(models.Model):
    incident_id = models.CharField(max_length=32, unique=True, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    severity = models.CharField(max_length=16, choices=IncidentSeverity.choices,
                                default=IncidentSeverity.MEDIUM)
    status = models.CharField(max_length=16, choices=IncidentStatus.choices,
                              default=IncidentStatus.OPEN, db_index=True)
    source = models.CharField(max_length=16, choices=LogSource.choices,
                              default=LogSource.BACKEND)
    module = models.CharField(max_length=255, blank=True, default='')
    assigned_engineer = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='assigned_incidents')
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='created_incidents')
    resolution_notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.incident_id:
            self.incident_id = _code('INC')
        if self.status in (IncidentStatus.RESOLVED, IncidentStatus.CLOSED) and not self.resolved_at:
            from django.utils import timezone
            self.resolved_at = timezone.now()
        if self.status not in (IncidentStatus.RESOLVED, IncidentStatus.CLOSED):
            self.resolved_at = None
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.incident_id} {self.title}"


class ErrorLog(models.Model):
    error_id = models.CharField(max_length=32, unique=True, editable=False)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    severity = models.CharField(max_length=16, choices=LogSeverity.choices,
                                default=LogSeverity.ERROR, db_index=True)
    category = models.CharField(max_length=32, choices=LogCategory.choices,
                                default=LogCategory.SYSTEM, db_index=True)
    source = models.CharField(max_length=16, choices=LogSource.choices,
                              default=LogSource.BACKEND, db_index=True)
    module = models.CharField(max_length=255, blank=True, default='', db_index=True)
    endpoint = models.CharField(max_length=500, blank=True, default='')
    method = models.CharField(max_length=10, blank=True, default='')
    status_code = models.PositiveSmallIntegerField(null=True, blank=True)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,
                             related_name='error_logs')
    user_role = models.CharField(max_length=30, blank=True, default='')
    correlation_id = models.CharField(max_length=64, blank=True, default='', db_index=True)
    exception_type = models.CharField(max_length=255, blank=True, default='')
    message = models.TextField(blank=True, default='')
    stack_trace = models.TextField(blank=True, default='')
    environment = models.CharField(max_length=32, blank=True, default='')
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True, default='')
    metadata = models.JSONField(default=dict, blank=True)
    resolution_status = models.CharField(
        max_length=16, choices=LogResolutionStatus.choices,
        default=LogResolutionStatus.NEW, db_index=True)
    incident = models.ForeignKey(Incident, null=True, blank=True, on_delete=models.SET_NULL,
                                 related_name='logs')
    acknowledged_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,
                                        related_name='acknowledged_errors')
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,
                                    related_name='resolved_errors')
    resolved_at = models.DateTimeField(null=True, blank=True)
    archived = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp', 'severity']),
            models.Index(fields=['correlation_id', 'timestamp']),
        ]

    def save(self, *args, **kwargs):
        if not self.error_id:
            self.error_id = _code('ERR')
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.error_id} [{self.severity}] {self.message[:80]}"


class SystemEvent(models.Model):
    event_id = models.CharField(max_length=32, unique=True, editable=False)
    category = models.CharField(max_length=32, choices=EventCategory.choices,
                                default=EventCategory.SYSTEM, db_index=True)
    action = models.CharField(max_length=120, db_index=True)
    actor = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,
                              related_name='system_events')
    actor_role = models.CharField(max_length=30, blank=True, default='')
    target_type = models.CharField(max_length=100, blank=True, default='')
    target_id = models.CharField(max_length=64, blank=True, default='')
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    correlation_id = models.CharField(max_length=64, blank=True, default='')
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    archived = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['category', 'timestamp']),
            models.Index(fields=['actor', 'timestamp']),
        ]

    def save(self, *args, **kwargs):
        if not self.event_id:
            self.event_id = _code('EVT')
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.event_id} {self.category}:{self.action}"


class IncidentUpdate(models.Model):
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name='updates')
    author = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,
                               related_name='incident_updates')
    status = models.CharField(max_length=16, choices=IncidentStatus.choices,
                              default=IncidentStatus.OPEN)
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Update on {self.incident_id} by {self.author_id}"


class IncidentRCA(models.Model):
    incident = models.OneToOneField(Incident, on_delete=models.CASCADE, related_name='rca')
    root_cause = models.TextField(blank=True, default='')
    impact = models.TextField(blank=True, default='')
    fix = models.TextField(blank=True, default='')
    preventive_action = models.TextField(blank=True, default='')
    related_deployment = models.CharField(max_length=255, blank=True, default='')
    related_commit = models.CharField(max_length=255, blank=True, default='')
    lessons_learned = models.TextField(blank=True, default='')
    documented_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,
                                      related_name='documented_rcas')
    documented_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Root Cause Analysis'

    def __str__(self):
        return f"RCA for {self.incident_id}"


class Alert(models.Model):
    alert_id = models.CharField(max_length=32, unique=True, editable=False)
    title = models.CharField(max_length=255)
    message = models.TextField(blank=True, default='')
    severity = models.CharField(max_length=16, choices=LogSeverity.choices,
                                default=LogSeverity.ERROR, db_index=True)
    category = models.CharField(max_length=32, choices=LogCategory.choices,
                                default=LogCategory.SYSTEM, db_index=True)
    module = models.CharField(max_length=255, blank=True, default='')
    correlation_id = models.CharField(max_length=64, blank=True, default='')
    error = models.ForeignKey(ErrorLog, null=True, blank=True, on_delete=models.SET_NULL,
                              related_name='alerts')
    channels = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,
                                        related_name='acknowledged_alerts')

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.alert_id:
            self.alert_id = _code('ALR')
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.alert_id} {self.title}"
