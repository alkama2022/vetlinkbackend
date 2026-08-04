from django.db import models
from apps.core.models import TimeStampedModel
from apps.patients.models import Patient


class CaseNote(TimeStampedModel):
    note_code = models.CharField(max_length=30, unique=True, db_index=True) # e.g. CN001
    patient = models.ForeignKey(Patient, on_delete=models.SET_NULL, null=True, blank=True, related_name='case_notes')
    patient_id_str = models.CharField(max_length=50, blank=True, default='')
    owner_name = models.CharField(max_length=255)
    animal = models.CharField(max_length=255)
    date = models.CharField(max_length=20) # YYYY-MM-DD
    vet_name = models.CharField(max_length=255)
    diagnosis = models.TextField()
    treatment = models.TextField()
    follow_up_date = models.CharField(max_length=20, blank=True, default='') # YYYY-MM-DD
    notes = models.TextField(blank=True, default='')

    def __str__(self):
        return f"{self.note_code} - {self.animal} ({self.owner_name}) - Diagnosis: {self.diagnosis[:30]}"
