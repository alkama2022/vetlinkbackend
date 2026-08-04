import uuid
from django.db import models
from django.utils import timezone


class SoftDeleteQuerySet(models.QuerySet):
    def delete(self):
        return super().update(is_deleted=True, deleted_at=timezone.now())

    def hard_delete(self):
        return super().delete()

    def alive(self):
        return self.filter(is_deleted=False)

    def dead(self):
        return self.filter(is_deleted=True)


class SoftDeleteManager(models.Manager):
    def __init__(self, *args, **kwargs):
        self._with_deleted = kwargs.pop('with_deleted', False)
        super().__init__(*args, **kwargs)

    def get_queryset(self):
        if self._with_deleted:
            return SoftDeleteQuerySet(self.model, using=self._db)
        return SoftDeleteQuerySet(self.model, using=self._db).filter(is_deleted=False)


class TimeStampedModel(models.Model):
    """
    Abstract base model providing UUID primary keys, timestamp fields,
    soft deletion, and audit tracking.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = SoftDeleteManager(with_deleted=True)

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at'])

    def hard_delete(self):
        super().delete()


class AuditLog(models.Model):
    """Immutable audit log for important create/update/delete actions."""
    ACTION_CHOICES = (
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    user_id = models.UUIDField(null=True, blank=True)
    username = models.CharField(max_length=255, blank=True, default='')
    role = models.CharField(max_length=64, blank=True, default='')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    resource_type = models.CharField(max_length=255, db_index=True)
    resource_id = models.CharField(max_length=255, blank=True, default='')
    summary = models.TextField(blank=True, default='')
    metadata = models.JSONField(blank=True, default=dict)

    class Meta:
        indexes = [models.Index(fields=['resource_type', 'resource_id'])]
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.timestamp.isoformat()} {self.action} {self.resource_type}:{self.resource_id} by {self.username or self.user_id}"
