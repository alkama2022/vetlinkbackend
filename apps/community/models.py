import uuid
from django.db import models
from apps.core.models import TimeStampedModel
from apps.accounts.models import User


class CommunityCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True)

    def __str__(self):
        return self.name


class CommunityTag(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class CommunityPost(TimeStampedModel):
    VISIBILITY_CHOICES = (('public', 'Public'), ('private', 'Private'), ('hidden', 'Hidden'))

    title = models.CharField(max_length=300)
    content = models.TextField()  # Rich text (HTML/Markdown)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='community_posts')
    author_name = models.CharField(max_length=255)
    author_role = models.CharField(max_length=64, blank=True, default='')
    author_avatar = models.URLField(blank=True, default='')
    category = models.ForeignKey(CommunityCategory, null=True, blank=True, on_delete=models.SET_NULL, related_name='posts')
    tags = models.ManyToManyField(CommunityTag, blank=True, related_name='posts')
    species = models.CharField(max_length=120, blank=True, default='')
    disease_category = models.CharField(max_length=120, blank=True, default='')
    location = models.CharField(max_length=255, blank=True, default='')
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='public', db_index=True)
    is_edited = models.BooleanField(default=False, db_index=True)

    def save(self, *args, **kwargs):
        if self.pk:
            self.is_edited = True
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} by {self.author_name}"


class CommunityComment(TimeStampedModel):
    post = models.ForeignKey(CommunityPost, on_delete=models.CASCADE, related_name='comments')
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='community_comments')
    content = models.TextField()
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"Comment by {self.author.email} on {self.post.title}"


class CommunityReaction(models.Model):
    REACTION_CHOICES = (
        ('like', 'Like'),
        ('helpful', 'Helpful'),
        ('thanks', 'Thanks'),
        ('insightful', 'Insightful'),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(CommunityPost, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='community_reactions')
    reaction = models.CharField(max_length=20, choices=REACTION_CHOICES)

    class Meta:
        unique_together = ('post', 'user', 'reaction')

    def __str__(self):
        return f"{self.reaction} by {self.user.email} on {self.post.title}"


class CommunityBookmark(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='community_bookmarks')
    post = models.ForeignKey(CommunityPost, on_delete=models.CASCADE, related_name='bookmarks')

    class Meta:
        unique_together = ('user', 'post')


class CommunityReport(models.Model):
    STATUS_CHOICES = (('open', 'Open'), ('reviewed', 'Reviewed'), ('dismissed', 'Dismissed'))
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='community_reports')
    post = models.ForeignKey(CommunityPost, on_delete=models.CASCADE, related_name='reports')
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    reviewed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='community_reports_reviewed')

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Report by {self.reporter.email} on {self.post.title}"
