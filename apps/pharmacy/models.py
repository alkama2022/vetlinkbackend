from django.db import models
from apps.core.models import TimeStampedModel


class DrugStock(TimeStampedModel):
    drug_code = models.CharField(max_length=30, unique=True, db_index=True) # e.g. D001
    name = models.CharField(max_length=255) # e.g. Ivermectin
    category = models.CharField(max_length=100) # e.g. Antiparasitic, Antibiotic, Vaccine
    quantity = models.PositiveIntegerField(default=0)
    unit = models.CharField(max_length=50) # e.g. vials, bottles, doses, tablets
    reorder_level = models.PositiveIntegerField(default=10)
    expiry_date = models.CharField(max_length=20) # YYYY-MM-DD
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00) # ₦
    facility_name = models.CharField(max_length=255, blank=True, default='') # e.g. Kano Vet Pharmacy
    facility_location = models.CharField(max_length=255, blank=True, default='') # e.g. Tudun Wada, Kano
    facility_lga = models.CharField(max_length=100, blank=True, default='', db_index=True) # e.g. Kano Municipal
    contact_phone = models.CharField(max_length=20, blank=True, default='')
    is_available = models.BooleanField(default=True) # Can be set false when out of stock
    last_restocked = models.DateField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['name', 'facility_lga'], name='idx_drug_name_lga'),
            models.Index(fields=['category', 'is_available'], name='idx_drug_cat_avail'),
            models.Index(fields=['facility_lga', 'is_available'], name='idx_drug_lga_avail'),
        ]

    def __str__(self):
        return f"{self.drug_code} - {self.name} ({self.quantity} {self.unit})"

    @property
    def is_low_stock(self):
        return self.quantity <= self.reorder_level
