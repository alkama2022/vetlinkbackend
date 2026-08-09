from django.db import migrations

CATEGORIES = [
    ("Livestock", "livestock"),
    ("Poultry", "poultry"),
    ("Feed & Forage", "feed-forage"),
    ("Veterinary Medicine", "veterinary-medicine"),
    ("Equipment & Tools", "equipment-tools"),
    ("Farm Services", "farm-services"),
    ("Transport & Logistics", "transport-logistics"),
]


def seed_categories(apps, schema_editor):
    MarketplaceCategory = apps.get_model("marketplace", "MarketplaceCategory")
    for name, slug in CATEGORIES:
        MarketplaceCategory.objects.get_or_create(slug=slug, defaults={"name": name})


def unseed_categories(apps, schema_editor):
    MarketplaceCategory = apps.get_model("marketplace", "MarketplaceCategory")
    MarketplaceCategory.objects.filter(slug__in=[slug for _, slug in CATEGORIES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("marketplace", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_categories, unseed_categories),
    ]
