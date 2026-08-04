from django.db import models
from apps.core.models import TimeStampedModel
from apps.patients.models import Patient


class Invoice(TimeStampedModel):
    class StatusChoices(models.TextChoices):
        UNPAID = 'Unpaid', 'Unpaid'
        PAID = 'Paid', 'Paid'
        WAIVED = 'Waived', 'Waived'

    invoice_code = models.CharField(max_length=30, unique=True, db_index=True) # e.g. INV-001
    patient = models.ForeignKey(Patient, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    patient_id_str = models.CharField(max_length=50, blank=True, default='')
    owner_name = models.CharField(max_length=255)
    animal = models.CharField(max_length=255)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00) # ₦
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.UNPAID, db_index=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.invoice_code} - {self.owner_name} (₦{self.total}) [{self.status}]"


class InvoiceItem(TimeStampedModel):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='services')
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.description} - ₦{self.amount}"
