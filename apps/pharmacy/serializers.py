from rest_framework import serializers
from .models import DrugStock


class DrugStockSerializer(serializers.ModelSerializer):
    reorderLevel = serializers.IntegerField(source='reorder_level')
    expiryDate = serializers.CharField(source='expiry_date')
    unitCost = serializers.DecimalField(source='unit_cost', max_digits=10, decimal_places=2)
    facilityName = serializers.CharField(source='facility_name', required=False, allow_blank=True, default='')
    facilityLocation = serializers.CharField(source='facility_location', required=False, allow_blank=True, default='')
    facilityLga = serializers.CharField(source='facility_lga', required=False, allow_blank=True, default='')
    contactPhone = serializers.CharField(source='contact_phone', required=False, allow_blank=True, default='')
    isAvailable = serializers.BooleanField(source='is_available', required=False, default=True)
    lastRestocked = serializers.DateField(source='last_restocked', allow_null=True, required=False)
    isLowStock = serializers.BooleanField(source='is_low_stock', read_only=True)

    class Meta:
        model = DrugStock
        fields = [
            'id', 'drug_code', 'name', 'category', 'quantity', 'unit',
            'reorderLevel', 'expiryDate', 'unitCost', 'facilityName',
            'facilityLocation', 'facilityLga', 'contactPhone', 'isAvailable',
            'lastRestocked', 'isLowStock', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'drug_code', 'created_at', 'updated_at']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['id'] = instance.drug_code if instance.drug_code else str(instance.id)
        return ret


class MedicineFinderSerializer(serializers.ModelSerializer):
    """Read-only serializer for public medicine search."""
    unitCost = serializers.DecimalField(source='unit_cost', max_digits=10, decimal_places=2)
    facilityName = serializers.CharField(source='facility_name')
    facilityLocation = serializers.CharField(source='facility_location')
    facilityLga = serializers.CharField(source='facility_lga')
    contactPhone = serializers.CharField(source='contact_phone')
    isAvailable = serializers.BooleanField(source='is_available')
    isLowStock = serializers.BooleanField(source='is_low_stock', read_only=True)

    class Meta:
        model = DrugStock
        fields = [
            'id', 'drug_code', 'name', 'category', 'quantity', 'unit',
            'unitCost', 'facilityName', 'facilityLocation', 'facilityLga',
            'contactPhone', 'isAvailable', 'isLowStock',
        ]
