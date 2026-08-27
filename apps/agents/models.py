from django.db import models
from django.conf import settings
from apps.core.models import TimeStampedModel


class Agent(TimeStampedModel):
    """Farmer-Agent network — trusted community members who help register farmers."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='agent_profile')
    agent_code = models.CharField(max_length=30, unique=True, db_index=True)
    lga = models.CharField(max_length=100, db_index=True)
    village = models.CharField(max_length=255, blank=True, default='')
    phone = models.CharField(max_length=20)
    total_registrations = models.PositiveIntegerField(default=0)
    total_reports_assisted = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)

    class Meta:
        ordering = ['-total_registrations']

    def __str__(self):
        return f"Agent {self.agent_code} - {self.user.get_full_name()}"


class AgentFarmerLink(TimeStampedModel):
    """Tracks which farmers an agent has registered."""
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='farmers')
    farmer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='registered_by_agent')
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('agent', 'farmer')
