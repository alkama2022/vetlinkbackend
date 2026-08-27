from django.db import models
from django.utils import timezone
from apps.core.models import TimeStampedModel


class HealthTip(TimeStampedModel):
    """Daily health tips sent via SMS/push."""
    SPECIES_CHOICES = [
        ('all', 'All Species'),
        ('poultry', 'Poultry'),
        ('cattle', 'Cattle'),
        ('goat', 'Goat'),
        ('sheep', 'Sheep'),
    ]

    tip_code = models.CharField(max_length=30, unique=True, db_index=True)
    title = models.CharField(max_length=255)
    content = models.TextField()
    species = models.CharField(max_length=20, choices=SPECIES_CHOICES, default='all')
    season = models.CharField(max_length=20, blank=True, default='')  # dry, rainy, cool
    language = models.CharField(max_length=5, default='en')  # en, ha
    is_active = models.BooleanField(default=True)
    sent_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.tip_code} - {self.title}"
