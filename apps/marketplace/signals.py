from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.notifications.models import Notification
from apps.accounts.models import User
from .models import MarketplaceComment, MarketplaceReaction, MarketplaceBookmark, MarketplaceMessage, MarketplaceReport


@receiver(post_save, sender=MarketplaceComment)
def notify_on_comment(sender, instance: MarketplaceComment, created, **kwargs):
    if not created:
        return
    listing = instance.listing
    recipient = listing.seller
    Notification.objects.create(
        notif_code=f'MP_COMMENT_{instance.id.hex[:8]}',
        title='New comment on your listing',
        body=f'{instance.author.full_name} commented: {instance.content[:200]}',
        tone=Notification.ToneChoices.INFO,
        recipient=recipient
    )


@receiver(post_save, sender=MarketplaceReaction)
def notify_on_reaction(sender, instance: MarketplaceReaction, created, **kwargs):
    if not created:
        return
    listing = instance.listing
    recipient = listing.seller
    Notification.objects.create(
        notif_code=f'MP_REACT_{instance.id.hex[:8]}',
        title='Someone liked your listing',
        body=f'{instance.user.full_name} reacted ({instance.reaction}) to {listing.title}',
        tone=Notification.ToneChoices.INFO,
        recipient=recipient
    )


@receiver(post_save, sender=MarketplaceBookmark)
def notify_on_bookmark(sender, instance: MarketplaceBookmark, created, **kwargs):
    if not created:
        return
    listing = instance.listing
    recipient = listing.seller
    Notification.objects.create(
        notif_code=f'MP_BOOK_{instance.id.hex[:8]}',
        title='Your listing was saved',
        body=f'{instance.user.full_name} saved your listing: {listing.title}',
        tone=Notification.ToneChoices.INFO,
        recipient=recipient
    )


@receiver(post_save, sender=MarketplaceReport)
def notify_on_report(sender, instance: MarketplaceReport, created, **kwargs):
    if not created:
        return
    # notify admins
    admins = User.objects.filter(is_superuser=True)
    for admin in admins:
        Notification.objects.create(
            notif_code=f'MP_REPORT_{instance.id.hex[:8]}_{admin.id.hex[:6]}',
            title='Marketplace report submitted',
            body=f'Report by {instance.reporter.full_name} for listing {instance.listing.title}: {instance.reason}',
            tone=Notification.ToneChoices.WARNING,
            recipient=admin
        )


@receiver(post_save, sender=MarketplaceMessage)
def notify_on_message(sender, instance: MarketplaceMessage, created, **kwargs):
    if not created:
        return
    conv = instance.conversation
    # determine recipient
    recipient = conv.seller if instance.sender_id != conv.seller_id else conv.buyer
    Notification.objects.create(
        notif_code=f'MP_MSG_{instance.id.hex[:8]}',
        title='New message about your listing',
        body=f'New message from {instance.sender.full_name}: {instance.content[:200]}',
        tone=Notification.ToneChoices.INFO,
        recipient=recipient
    )
