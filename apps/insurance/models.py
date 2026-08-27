from django.db import models
from django.conf import settings
from apps.core.models import TimeStampedModel


class InsuranceProvider(TimeStampedModel):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=20, unique=True)
    api_key = models.CharField(max_length=255, blank=True, default='')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class LivestockInsurance(TimeStampedModel):
    class StatusChoices(models.TextChoices):
        ACTIVE = 'Active', 'Active'
        EXPIRED = 'Expired', 'Expired'
        CLAIMED = 'Claimed', 'Claimed'
        CANCELLED = 'Cancelled', 'Cancelled'

    policy_number = models.CharField(max_length=50, unique=True, db_index=True)
    animal = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='insurance_policies')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='livestock_insurance')
    provider = models.ForeignKey(InsuranceProvider, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.ACTIVE)
    premium = models.DecimalField(max_digits=10, decimal_places=2)
    coverage_amount = models.DecimalField(max_digits=12, decimal_places=2)
    start_date = models.DateField()
    end_date = models.DateField()
    last_verified = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['owner', 'status'], name='idx_insurance_owner_status'),
            models.Index(fields=['animal', 'status'], name='idx_insurance_animal_status'),
        ]

    def __str__(self):
        return f"{self.policy_number} - {self.animal}"
