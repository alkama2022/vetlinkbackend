from rest_framework import serializers
from .models import Invoice, InvoiceItem


class InvoiceItemSerializer(serializers.ModelSerializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        model = InvoiceItem
        fields = ['id', 'description', 'amount']
        read_only_fields = ['id']


class InvoiceSerializer(serializers.ModelSerializer):
    patientId = serializers.CharField(source='patient_id_str', required=False, allow_blank=True)
    ownerName = serializers.CharField(source='owner_name')
    services = InvoiceItemSerializer(many=True)
    total = serializers.DecimalField(max_digits=12, decimal_places=2)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    paidAt = serializers.DateTimeField(source='paid_at', required=False, allow_null=True)

    class Meta:
        model = Invoice
        fields = ['id', 'invoice_code', 'patientId', 'ownerName', 'animal', 'services', 'total', 'status', 'createdAt', 'paidAt']
        read_only_fields = ['id', 'createdAt']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['id'] = instance.invoice_code if instance.invoice_code else str(instance.id)
        if instance.patient:
            ret['patientId'] = instance.patient.patient_code
        return ret

    def create(self, validated_data):
        services_data = validated_data.pop('services', [])
        patient_id_str = validated_data.get('patient_id_str', '')
        if not validated_data.get('invoice_code'):
            import time
            validated_data['invoice_code'] = f"INV-{str(int(time.time()))[-6:]}"

        invoice = Invoice.objects.create(**validated_data)

        total_calc = 0
        for s in services_data:
            item = InvoiceItem.objects.create(invoice=invoice, **s)
            total_calc += item.amount

        if total_calc > 0 and invoice.total == 0:
            invoice.total = total_calc
            invoice.save(update_fields=['total'])

        return invoice
