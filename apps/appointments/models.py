from django.db import models
from apps.core.models import TimeStampedModel
from apps.patients.models import Patient


class Appointment(TimeStampedModel):
    class StatusChoices(models.TextChoices):
        SCHEDULED = 'Scheduled', 'Scheduled'
        IN_PROGRESS = 'In progress', 'In progress'
        COMPLETED = 'Completed', 'Completed'
        CANCELLED = 'Cancelled', 'Cancelled'

    appointment_code = models.CharField(max_length=30, unique=True, db_index=True) # e.g. A001
    patient = models.ForeignKey(Patient, on_delete=models.SET_NULL, null=True, blank=True, related_name='appointments')
    patient_id_str = models.CharField(max_length=50, blank=True, default='')
    time = models.CharField(max_length=10) # HH:MM e.g. "09:00"
    date = models.CharField(max_length=20) # YYYY-MM-DD e.g. "2024-05-22"
    owner_name = models.CharField(max_length=255)
    animal = models.CharField(max_length=255) # e.g. "Poultry · 250 birds"
    reason = models.CharField(max_length=255) # e.g. "Flock health check"
    notes = models.TextField(blank=True, default='')
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.SCHEDULED,
        db_index=True
    )

    def __str__(self):
        return f"{self.appointment_code} ({self.time} - {self.date}) - {self.owner_name} - {self.status}"

    class Meta:
        indexes = [
            models.Index(fields=['status', 'date'], name='idx_appt_status_date'),
            models.Index(fields=['patient', 'date'], name='idx_appt_patient_date'),
        ]
