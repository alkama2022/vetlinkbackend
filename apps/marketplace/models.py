import uuid
from django.db import models
from django.conf import settings


class MarketplaceCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


def upload_to_listing(instance, filename):
    return f'marketplace/listings/{instance.listing.id}/{filename}'


class MarketplaceListing(models.Model):
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('reserved', 'Reserved'),
        ('sold', 'Sold'),
    ]
    CONDITION_CHOICES = [('new', 'New'), ('used', 'Used')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='marketplace_listings', on_delete=models.CASCADE)
    title = models.CharField(max_length=300)
    category = models.ForeignKey('MarketplaceCategory', null=True, blank=True, on_delete=models.SET_NULL, related_name='listings')
    description = models.TextField()
    price = models.DecimalField(max_digits=12, decimal_places=2, db_index=True)
    negotiable = models.BooleanField(default=False)
    quantity = models.FloatField(default=1)
    unit = models.CharField(max_length=64, default='unit')
    condition = models.CharField(max_length=10, choices=CONDITION_CHOICES, default='used')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available', db_index=True)
    location = models.CharField(max_length=255, blank=True, default='')
    contact_preference = models.CharField(max_length=32, default='chat')
    delivery_options = models.JSONField(default=list, blank=True)
    tags = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class MarketplaceImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(MarketplaceListing, related_name='images', on_delete=models.CASCADE)
    file = models.ImageField(upload_to=upload_to_listing)
    alt_text = models.CharField(max_length=255, blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order']


class MarketplaceVideo(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(MarketplaceListing, related_name='videos', on_delete=models.CASCADE)
    file = models.FileField(upload_to=upload_to_listing)
    thumbnail = models.ImageField(upload_to=upload_to_listing, null=True, blank=True)


class MarketplaceDocument(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(MarketplaceListing, related_name='documents', on_delete=models.CASCADE)
    file = models.FileField(upload_to=upload_to_listing)
    doc_type = models.CharField(max_length=80, blank=True)


class MarketplaceComment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(MarketplaceListing, related_name='comments', on_delete=models.CASCADE)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='marketplace_comments', on_delete=models.CASCADE)
    parent = models.ForeignKey('self', null=True, blank=True, related_name='replies', on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']


class MarketplaceReaction(models.Model):
    REACTION_CHOICES = [('like', 'Like'), ('helpful', 'Helpful'), ('interesting', 'Interesting')]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(MarketplaceListing, related_name='reactions', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='marketplace_reactions', on_delete=models.CASCADE)
    reaction = models.CharField(max_length=20, choices=REACTION_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('listing', 'user', 'reaction')


class MarketplaceBookmark(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(MarketplaceListing, related_name='bookmarks', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='marketplace_bookmarks', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('listing', 'user')
        ordering = ['-created_at']


class MarketplaceReport(models.Model):
    REASON_CHOICES = [('fraud', 'Fraud'), ('inappropriate', 'Inappropriate'), ('spam', 'Spam'), ('duplicate', 'Duplicate')]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(MarketplaceListing, related_name='reports', on_delete=models.CASCADE)
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='marketplace_reports', on_delete=models.CASCADE)
    reason = models.CharField(max_length=80, choices=REASON_CHOICES)
    details = models.TextField(blank=True)
    status = models.CharField(max_length=20, default='open')
    created_at = models.DateTimeField(auto_now_add=True)


class MarketplaceConversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(MarketplaceListing, related_name='conversations', on_delete=models.CASCADE)
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='marketplace_conversations', on_delete=models.CASCADE)
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='marketplace_conversations_sold', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']


class MarketplaceMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(MarketplaceConversation, related_name='messages', on_delete=models.CASCADE)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='marketplace_messages', on_delete=models.CASCADE)
    content = models.TextField(blank=True)
    attachment = models.FileField(upload_to=upload_to_listing, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ['created_at']


class MarketplaceRating(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(MarketplaceListing, related_name='ratings', on_delete=models.CASCADE)
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='marketplace_ratings', on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField()  # 1-5
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('listing', 'reviewer')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.reviewer} rated {self.listing} {self.rating}/5"
