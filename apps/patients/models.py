from django.db import models
from apps.core.models import TimeStampedModel
from apps.accounts.models import User


class Patient(TimeStampedModel):
    patient_code = models.CharField(max_length=30, unique=True, db_index=True) # e.g. P001
    owner_name = models.CharField(max_length=255)
    owner_phone = models.CharField(max_length=30)
    lga = models.CharField(max_length=100, db_index=True)
    species = models.CharField(max_length=100) # e.g. Poultry (Chicken), Cattle, Goat / Sheep
    animal_name = models.CharField(max_length=255) # e.g. Flock A, Nanny, Rex
    animal_age = models.CharField(max_length=100) # e.g. 6 months, 3 years
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='patients')

    def __str__(self):
        return f"{self.patient_code} - {self.animal_name} ({self.owner_name})"
