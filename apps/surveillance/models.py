from django.db import models
from django.utils import timezone
from apps.core.models import TimeStampedModel
from apps.accounts.models import User


class DiseaseReport(TimeStampedModel):
    class AlertStatusChoices(models.TextChoices):
        SUSPECTED = 'Suspected', 'Suspected'
        UNDER_INVESTIGATION = 'Under investigation', 'Under investigation'
        CONFIRMED = 'Confirmed', 'Confirmed'
        CLOSED = 'Closed', 'Closed'

    report_code = models.CharField(max_length=30, unique=True, db_index=True) # e.g. VK100001
    species = models.CharField(max_length=100) # e.g. Poultry (Chicken), Cattle
    disease = models.CharField(max_length=255) # e.g. Avian Influenza (Bird Flu), Anthrax
    affected = models.PositiveIntegerField(default=0)
    dead = models.PositiveIntegerField(default=0)
    signs = models.JSONField(default=list) # Array of sign strings
    date = models.CharField(max_length=20) # YYYY-MM-DD
    location = models.CharField(max_length=255) # e.g. Dawakin Kudu, Kano State
    lga = models.CharField(max_length=100, db_index=True) # Extracted LGA name e.g. Dawakin Kudu
    coords = models.CharField(max_length=100, blank=True, default='') # GPS Coordinates e.g. "11.8500, 8.6167"
    notes = models.TextField(blank=True, default='')
    photos = models.JSONField(default=list, blank=True)  # Stored relative paths of evidence photos/videos
    submitted_at = models.DateTimeField(default=timezone.now)
    farmer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='disease_reports')
    farmer_name = models.CharField(max_length=255, blank=True, default='')
    alert_status = models.CharField(
        max_length=30,
        choices=AlertStatusChoices.choices,
        default=AlertStatusChoices.SUSPECTED,
        db_index=True
    )

    class Meta:
        indexes = [
            models.Index(fields=['alert_status', '-submitted_at'], name='idx_disease_status_date'),
            models.Index(fields=['species', 'alert_status'], name='idx_disease_species_status'),
            models.Index(fields=['lga', '-submitted_at'], name='idx_disease_lga_date'),
        ]

    def __str__(self):
        return f"{self.report_code} - {self.disease} in {self.lga} ({self.alert_status})"
