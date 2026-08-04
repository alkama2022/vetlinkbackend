from django.db import models
from django.utils import timezone
from apps.core.models import TimeStampedModel
from apps.accounts.models import User


class Notification(TimeStampedModel):
    class ToneChoices(models.TextChoices):
        INFO = 'info', 'Info'
        WARNING = 'warning', 'Warning'
        DANGER = 'danger', 'Danger'
        SUCCESS = 'success', 'Success'

    notif_code = models.CharField(max_length=30, unique=True, db_index=True) # e.g. N001
    title = models.CharField(max_length=255)
    body = models.TextField()
    tone = models.CharField(max_length=20, choices=ToneChoices.choices, default=ToneChoices.INFO)
    read = models.BooleanField(default=False, db_index=True)
    recipient = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications')
    created_at_override = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.notif_code} - {self.title} [{self.tone}] (Read: {self.read})"
