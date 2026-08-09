from rest_framework import serializers
from .models import DrugStock


class DrugStockSerializer(serializers.ModelSerializer):
    reorderLevel = serializers.IntegerField(source='reorder_level')
    expiryDate = serializers.CharField(source='expiry_date')
    unitCost = serializers.DecimalField(source='unit_cost', max_digits=10, decimal_places=2)

    class Meta:
        model = DrugStock
        fields = ['id', 'drug_code', 'name', 'category', 'quantity', 'unit', 'reorderLevel', 'expiryDate', 'unitCost', 'created_at', 'updated_at']
        read_only_fields = ['id', 'drug_code', 'created_at', 'updated_at']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['id'] = instance.drug_code if instance.drug_code else str(instance.id)
        return ret
