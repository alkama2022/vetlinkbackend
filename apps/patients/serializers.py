from rest_framework import serializers
from .models import Patient


class PatientSerializer(serializers.ModelSerializer):
    # Frontend compat field aliases
    ownerName = serializers.CharField(source='owner_name')
    ownerPhone = serializers.CharField(source='owner_phone')
    animalName = serializers.CharField(source='animal_name')
    animalAge = serializers.CharField(source='animal_age')
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = Patient
        fields = [
            'id', 'patient_code', 'ownerName', 'ownerPhone', 'lga',
            'species', 'animalName', 'animalAge', 'createdAt'
        ]
        read_only_fields = ['id', 'createdAt']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # Ensure 'id' field outputs patient_code or id for frontend compatibility
        ret['id'] = instance.patient_code if instance.patient_code else str(instance.id)
        return ret
