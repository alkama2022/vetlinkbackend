from django.db import migrations


TEMPLATES = [
    # Poultry – Chicken
    ("Poultry (Chicken)", "Newcastle Disease (ND) – 1st", 1, 7, "Hatchery ND vaccination"),
    ("Poultry (Chicken)", "Infectious Bursal Disease (Gumboro) – 1st", 2, 14, "Gumboro first dose"),
    ("Poultry (Chicken)", "Newcastle Disease – 2nd (LaSota)", 3, 21, "Booster ND"),
    ("Poultry (Chicken)", "Fowl Pox", 4, 28, "Wing-web application"),
    ("Poultry (Chicken)", "Coccidiosis", 5, 30, "If not using medicated feed"),
    # Poultry – Turkey (shares chicken schedule but separate entry for icontains match)
    ("Poultry (Turkey)", "Newcastle Disease – 1st", 1, 7, "Turkey ND first dose"),
    ("Poultry (Turkey)", "Turkey Pox", 2, 21, "Wing-web"),
    ("Poultry (Turkey)", "Fowl Cholera", 3, 45, "Pasturella"),
    # Cattle
    ("Cattle", "Contagious Bovine Pleuropneumonia (CBPP)", 1, 90, "Annual CBPP"),
    ("Cattle", "Foot and Mouth Disease (FMD) – 1st", 2, 90, "FMD trivalent"),
    ("Cattle", "Anthrax", 3, 120, "Annual anthrax spore vaccine"),
    ("Cattle", "Brucellosis (S19) – heifers", 4, 180, "Calfhood vaccination"),
    # Goat
    ("Goat", "Peste des Petits Ruminants (PPR)", 1, 30, "PPR live vaccine"),
    ("Goat", "Contagious Caprine Pleuropneumonia (CCPP)", 2, 60, "CCPP inactivated"),
    ("Goat", "Anthrax", 3, 90, "Annual"),
    # Sheep
    ("Sheep", "Peste des Petits Ruminants (PPR)", 1, 30, "PPR"),
    ("Sheep", "Sheep Pox", 2, 60, "Live attenuated"),
    ("Sheep", "Anthrax", 3, 90, "Annual"),
    # Pig
    ("Pig", "Classical Swine Fever", 1, 45, "CSF live vaccine"),
    ("Pig", "Erysipelas", 2, 60, "Bacterin"),
    ("Pig", "Foot and Mouth Disease", 3, 90, "FMD"),
    # Dog
    ("Dog", "Rabies – 1st", 1, 90, "Rabies inactivated"),
    ("Dog", "DHPPi/L – 1st", 2, 60, "Distemper, Hepatitis, Parvo, Parainfluenza"),
    ("Dog", "DHPPi/L – 2nd", 3, 90, "Booster"),
    ("Dog", "Rabies – booster", 4, 365, "Annual rabies booster"),
    # Cat
    ("Cat", "Rabies – 1st", 1, 90, "Rabies"),
    ("Cat", "FVRCP – 1st", 2, 60, "Calicivirus, Rhinotracheitis, Panleukopenia"),
    ("Cat", "FVRCP – 2nd", 3, 90, "Booster"),
    # Fish
    ("Fish", "Aeromonas hydrophila", 1, 30, "Bath or injection"),
    ("Fish", "Vibrio – booster", 2, 60, "Second immersion"),
    # Rabbit
    ("Rabbit", "Myxomatosis", 1, 35, "Live vaccine"),
    ("Rabbit", "Rabbit Haemorrhagic Disease (RHD)", 2, 45, "RHD inactivated"),

    # Generic fallbacks for icontains = 'Poultry' base match (allows Poultry (Chicken) → Poultry)
    ("Poultry", "Newcastle Disease – generic", 1, 7, "Fallback for bare Poultry"),
    ("Goat / Sheep", "PPR – small ruminant", 1, 30, "Covers combined label from community tags"),
    ("Dog / Cat", "Rabies – combined", 1, 90, "Fallback for Dog / Cat label"),
    ("All Species", "Rabies – universal biosecurity", 1, 90, "Default where no species match"),
]


def seed_templates(apps, schema_editor):
    VaccineTemplate = apps.get_model("vaccinations", "VaccineTemplate")
    for species, vaccine_name, dose_number, age_days, notes in TEMPLATES:
        VaccineTemplate.objects.get_or_create(
            species=species,
            vaccine_name=vaccine_name,
            dose_number=dose_number,
            defaults={"age_days": age_days, "notes": notes, "is_active": True},
        )


def unseed_templates(apps, schema_editor):
    VaccineTemplate = apps.get_model("vaccinations", "VaccineTemplate")
    for species, vaccine_name, dose_number, _, _ in TEMPLATES:
        VaccineTemplate.objects.filter(
            species=species, vaccine_name=vaccine_name, dose_number=dose_number
        ).delete()


class Migration(migrations.Migration):
    dependencies = [("vaccinations", "0001_initial_vaccination")]
    operations = [migrations.RunPython(seed_templates, unseed_templates)]
