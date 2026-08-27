from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.db.models import Q
from apps.pharmacy.models import DrugStock
from apps.notifications.sms import notify_drug_stock_low


class Command(BaseCommand):
    help = "Check for expired and expiring-soon drugs, create notifications"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days", type=int, default=30,
            help="Alert for drugs expiring within N days (default: 30)",
        )

    def handle(self, *args, **options):
        days = options["days"]
        today = date.today()
        cutoff = today + timedelta(days=days)

        expired = []
        expiring = []
        low_stock = []

        for drug in DrugStock.objects.all():
            try:
                expiry = date.fromisoformat(drug.expiry_date)
            except (ValueError, TypeError):
                continue

            if expiry < today:
                expired.append(drug)
            elif expiry <= cutoff:
                expiring.append(drug)

            if drug.quantity <= drug.reorder_level:
                low_stock.append(drug)

        # Create notifications
        from apps.notifications.models import Notification

        for drug in expired:
            Notification.objects.get_or_create(
                user__role="PHARMACIST",
                title=f"EXPIRED: {drug.name}",
                defaults={
                    "user_id": None,
                    "message": f"{drug.name} ({drug.drug_code}) expired on {drug.expiry_date}. Remove from stock immediately.",
                    "category": "system",
                },
            )

        for drug in expiring:
            days_left = (date.fromisoformat(drug.expiry_date) - today).days
            Notification.objects.get_or_create(
                user__role="PHARMACIST",
                title=f"Expiring soon: {drug.name}",
                defaults={
                    "user_id": None,
                    "message": f"{drug.name} ({drug.drug_code}) expires in {days_left} days ({drug.expiry_date}).",
                    "category": "system",
                },
            )

        for drug in low_stock:
            Notification.objects.get_or_create(
                user__role="PHARMACIST",
                title=f"Low stock: {drug.name}",
                defaults={
                    "user_id": None,
                    "message": f"{drug.name} ({drug.drug_code}) has {drug.quantity} {drug.unit} left (reorder level: {drug.reorder_level}).",
                    "category": "system",
                },
            )

        # Send SMS alerts for critical items
        for drug in expired:
            try:
                pharmacists = DrugStock.objects.values_list("created_by__phone_number", flat=True).distinct()
                for phone in pharmacists:
                    if phone:
                        notify_drug_stock_low(drug.name, drug.quantity, drug.unit)
            except Exception:
                pass

        self.stdout.write(self.style.SUCCESS(
            f"Drug expiry check complete: {len(expired)} expired, "
            f"{len(expiring)} expiring within {days} days, {len(low_stock)} low stock"
        ))
