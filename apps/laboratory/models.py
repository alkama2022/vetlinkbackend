from django.db import models
from apps.core.models import TimeStampedModel
from apps.patients.models import Patient


class LabSample(TimeStampedModel):
    class StatusChoices(models.TextChoices):
        RECEIVED = 'Received', 'Received'
        IN_ANALYSIS = 'In analysis', 'In analysis'
        RESULT_READY = 'Result ready', 'Result ready'
        PUBLISHED = 'Published', 'Published'

    class PriorityChoices(models.TextChoices):
        URGENT = 'Urgent', 'Urgent'
        ROUTINE = 'Routine', 'Routine'

    sample_code = models.CharField(max_length=30, unique=True, db_index=True) # e.g. LAB-24-0912
    species = models.CharField(max_length=100)
    test = models.CharField(max_length=255) # e.g. AI PCR panel, Brucella ELISA
    facility = models.CharField(max_length=255) # e.g. Kano Vet Clinic
    status = models.CharField(max_length=30, choices=StatusChoices.choices, default=StatusChoices.RECEIVED, db_index=True)
    priority = models.CharField(max_length=20, choices=PriorityChoices.choices, default=PriorityChoices.ROUTINE, db_index=True)
    date_received = models.CharField(max_length=20) # YYYY-MM-DD
    patient = models.ForeignKey(Patient, on_delete=models.SET_NULL, null=True, blank=True, related_name='lab_samples')
    patient_id_str = models.CharField(max_length=50, blank=True, default='')
    requested_by = models.CharField(max_length=255, blank=True, default='')
    result_findings = models.TextField(blank=True, default='')
    result_positive = models.BooleanField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.sample_code} - {self.test} ({self.species}) - {self.status}"
