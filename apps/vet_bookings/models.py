from django.db import models
from django.utils import timezone
from apps.core.models import TimeStampedModel
from apps.accounts.models import User
from apps.veterinarians.models import VeterinarianProfile


class VetAvailability(TimeStampedModel):
    """Vet availability slots."""
    vet = models.ForeignKey(VeterinarianProfile, on_delete=models.CASCADE, related_name='availability_slots')
    date = models.DateField(db_index=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_booked = models.BooleanField(default=False)

    class Meta:
        ordering = ['date', 'start_time']
        indexes = [
            models.Index(fields=['vet', 'date', 'is_booked'], name='idx_vet_avail_vet_date'),
        ]

    def __str__(self):
        return f"{self.vet} - {self.date} {self.start_time}-{self.end_time}"


class VetBooking(TimeStampedModel):
    """Farmer bookings with vets."""
    class StatusChoices(models.TextChoices):
        PENDING = 'Pending', 'Pending'
        CONFIRMED = 'Confirmed', 'Confirmed'
        COMPLETED = 'Completed', 'Completed'
        CANCELLED = 'Cancelled', 'Cancelled'
        NO_SHOW = 'No show', 'No show'

    booking_code = models.CharField(max_length=30, unique=True, db_index=True)
    farmer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vet_bookings')
    vet = models.ForeignKey(VeterinarianProfile, on_delete=models.CASCADE, related_name='bookings')
    availability = models.OneToOneField(VetAvailability, on_delete=models.CASCADE, related_name='booking')
    animal_name = models.CharField(max_length=255)
    species = models.CharField(max_length=100)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING, db_index=True)
    notes = models.TextField(blank=True, default='')
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['farmer', 'status'], name='idx_vetbook_farmer_status'),
            models.Index(fields=['vet', 'status'], name='idx_vetbook_vet_status'),
        ]

    def __str__(self):
        return f"{self.booking_code} - {self.farmer} with {self.vet}"
