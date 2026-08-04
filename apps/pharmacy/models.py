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

    def __str__(self):
        return f"{self.drug_code} - {self.name} ({self.quantity} {self.unit})"

    @property
    def is_low_stock(self):
        return self.quantity <= self.reorder_level
