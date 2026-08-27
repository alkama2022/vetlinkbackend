from django.db import models
from django.utils import timezone
from apps.core.models import TimeStampedModel
from apps.accounts.models import User


class VaccineTemplate(TimeStampedModel):
    """Predefined vaccination schedules per species."""
    species = models.CharField(max_length=100, db_index=True)  # e.g. Poultry, Cattle, Goat
    vaccine_name = models.CharField(max_length=255)  # e.g. Newcastle Disease
    dose_number = models.PositiveIntegerField(default=1)  # 1st dose, 2nd dose, booster
    age_days = models.PositiveIntegerField(default=0)  # Days after birth/procurement
    interval_days = models.PositiveIntegerField(default=0)  # Days after previous dose
    notes = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['species', 'age_days']
        indexes = [
            models.Index(fields=['species', 'is_active'], name='idx_vax_template_species'),
        ]

    def __str__(self):
        return f"{self.species} - {self.vaccine_name} (Dose {self.dose_number})"


class VaccinationRecord(TimeStampedModel):
    """Actual vaccination given to an animal."""
    record_code = models.CharField(max_length=30, unique=True, db_index=True)
    animal_name = models.CharField(max_length=255)
    species = models.CharField(max_length=100)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vaccination_records')
    vaccine_name = models.CharField(max_length=255)
    dose_number = models.PositiveIntegerField(default=1)
    date_given = models.DateField(default=timezone.now)
    next_due_date = models.DateField(null=True, blank=True)
    administered_by = models.CharField(max_length=255, blank=True, default='')  # Vet name or clinic
    batch_number = models.CharField(max_length=100, blank=True, default='')
    notes = models.TextField(blank=True, default='')
    reminder_sent = models.BooleanField(default=False)

    class Meta:
        ordering = ['-date_given']
        indexes = [
            models.Index(fields=['owner', '-date_given'], name='idx_vaxrecord_owner_date'),
            models.Index(fields=['next_due_date', 'reminder_sent'], name='idx_vaxrecord_due_remind'),
        ]

    def __str__(self):
        return f"{self.animal_name} - {self.vaccine_name} ({self.date_given})"
