from django.db import models
from django.utils import timezone
from apps.core.models import TimeStampedModel
from apps.veterinarians.models import VeterinarianProfile
from apps.accounts.models import User


class ConsultationRequest(TimeStampedModel):
    class ChannelChoices(models.TextChoices):
        IN_APP = 'in-app', 'In-App'
        WHATSAPP = 'whatsapp', 'WhatsApp'

    class StatusChoices(models.TextChoices):
        PENDING = 'Pending', 'Pending'
        ACCEPTED = 'Accepted', 'Accepted'
        IN_PROGRESS = 'In progress', 'In progress'
        RESOLVED = 'Resolved', 'Resolved'
        CANCELLED = 'Cancelled', 'Cancelled'

    class SeverityChoices(models.TextChoices):
        MILD = 'Mild', 'Mild'
        MODERATE = 'Moderate', 'Moderate'
        SEVERE = 'Severe', 'Severe'
        CRITICAL = 'Critical', 'Critical'

    consultation_code = models.CharField(max_length=30, unique=True, db_index=True) # e.g. CON001
    farmer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='consultation_requests')
    farmer_name = models.CharField(max_length=255)
    farm_location = models.CharField(max_length=255)
    vet = models.ForeignKey(VeterinarianProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='consultation_requests')
    vet_id_str = models.CharField(max_length=50, blank=True, default='')
    vet_name = models.CharField(max_length=255)
    channel = models.CharField(max_length=20, choices=ChannelChoices.choices, default=ChannelChoices.IN_APP)
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING, db_index=True)

    disease_name = models.CharField(max_length=255, blank=True, default='')
    symptoms_en = models.TextField(blank=True, default='')
    symptoms_ha = models.TextField(blank=True, default='')
    species = models.CharField(max_length=100)
    breed = models.CharField(max_length=100, blank=True, default='')
    animal_age = models.CharField(max_length=100)
    animal_gender = models.CharField(max_length=20, default='Mixed')
    affected_count = models.PositiveIntegerField(default=1)
    duration_days = models.PositiveIntegerField(default=1)
    severity = models.CharField(max_length=20, choices=SeverityChoices.choices, default=SeverityChoices.MODERATE)
    additional_notes = models.TextField(blank=True, default='')

    photo_urls = models.JSONField(default=list)
    video_urls = models.JSONField(default=list)
    voice_urls = models.JSONField(default=list)

    submitted_at = models.DateTimeField(default=timezone.now)
    accepted_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.consultation_code} - {self.farmer_name} ({self.species}) -> {self.vet_name}"

    class Meta:
        indexes = [
            models.Index(fields=['status', '-submitted_at'], name='idx_consult_status_date'),
            models.Index(fields=['farmer', 'status'], name='idx_consult_farmer_status'),
            models.Index(fields=['vet', 'status'], name='idx_consult_vet_status'),
            models.Index(fields=['severity', 'status'], name='idx_consult_severity_status'),
        ]


class ChatMessage(TimeStampedModel):
    class SenderChoices(models.TextChoices):
        FARMER = 'farmer', 'Farmer'
        VET = 'vet', 'Veterinarian'

    message_code = models.CharField(max_length=30, unique=True, db_index=True) # e.g. M001
    consultation = models.ForeignKey(ConsultationRequest, on_delete=models.CASCADE, related_name='messages')
    sender = models.CharField(max_length=20, choices=SenderChoices.choices)
    sender_name = models.CharField(max_length=255)
    text = models.TextField()
    media_url = models.URLField(blank=True, null=True)
    media_type = models.CharField(max_length=20, blank=True, null=True) # image, video, voice, document
    sent_at = models.DateTimeField(default=timezone.now)
    read = models.BooleanField(default=False)

    def __str__(self):
        return f"Msg from {self.sender_name} on {self.consultation.consultation_code}"

    class Meta:
        indexes = [
            models.Index(fields=['consultation', '-sent_at'], name='idx_msg_consult_date'),
            models.Index(fields=['read', '-sent_at'], name='idx_msg_read_date'),
        ]
