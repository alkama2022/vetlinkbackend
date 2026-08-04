from django.db import models
from apps.core.models import TimeStampedModel
from apps.accounts.models import User


class FarmerHerd(TimeStampedModel):
    herd_code = models.CharField(max_length=30, unique=True, db_index=True) # e.g. H001
    type = models.CharField(max_length=100) # e.g. Poultry, Goats, Cattle
    count = models.CharField(max_length=100) # e.g. "250 birds", "15 livestock"
    healthy = models.PositiveIntegerField(default=100) # percentage e.g. 96
    farmer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='herds')

    def __str__(self):
        return f"{self.herd_code} - {self.type} ({self.count})"


class FarmerReminder(TimeStampedModel):
    class ToneChoices(models.TextChoices):
        WARNING = 'warning', 'Warning'
        DANGER = 'danger', 'Danger'
        INFO = 'info', 'Info'

    reminder_code = models.CharField(max_length=30, unique=True, db_index=True) # e.g. R001
    title = models.CharField(max_length=255)
    date = models.CharField(max_length=20) # YYYY-MM-DD
    tone = models.CharField(max_length=20, choices=ToneChoices.choices, default=ToneChoices.WARNING)
    done = models.BooleanField(default=False, db_index=True)
    farmer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reminders')

    def __str__(self):
        return f"{self.reminder_code} - {self.title} ({self.date}) [Done: {self.done}]"
