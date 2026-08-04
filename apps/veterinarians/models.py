from django.db import models
from apps.core.models import TimeStampedModel
from apps.accounts.models import User


class VeterinarianProfile(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='vet_profile', null=True, blank=True)
    vet_code = models.CharField(max_length=20, unique=True, db_index=True) # e.g. VET001
    full_name = models.CharField(max_length=255)
    license_number = models.CharField(max_length=100) # e.g. VCN/2015/4521
    qualifications = models.CharField(max_length=255) # e.g. DVM, MSc Poultry Health
    specializations = models.JSONField(default=list) # Array of specialization strings
    species_treated = models.JSONField(default=list) # Array of species strings
    diseases_expertise = models.JSONField(default=list) # Array of disease strings
    years_experience = models.PositiveIntegerField(default=0)
    languages = models.JSONField(default=list) # e.g. ["English", "Hausa"]
    clinic_name = models.CharField(max_length=255)
    clinic_address = models.TextField()
    lga = models.CharField(max_length=100, db_index=True)
    service_area = models.JSONField(default=list) # Array of LGAs covered
    whatsapp_number = models.CharField(max_length=30)
    phone = models.CharField(max_length=30)
    email = models.EmailField()
    available = models.BooleanField(default=True, db_index=True)
    available_online = models.BooleanField(default=True)
    available_emergency = models.BooleanField(default=True)
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00) # ₦
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=5.00) # 1.0 to 5.0
    total_consultations = models.PositiveIntegerField(default=0)
    bio = models.TextField(blank=True, default='')
    avatar_initials = models.CharField(max_length=5, blank=True, default='')

    def __str__(self):
        return f"{self.full_name} ({self.license_number}) - {self.clinic_name}"
