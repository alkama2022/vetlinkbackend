from rest_framework import serializers
from .models import CaseNote


class CaseNoteSerializer(serializers.ModelSerializer):
    patientId = serializers.CharField(source='patient_id_str', required=False, allow_blank=True)
    ownerName = serializers.CharField(source='owner_name')
    vetName = serializers.CharField(source='vet_name')
    followUpDate = serializers.CharField(source='follow_up_date', required=False, allow_blank=True)

    class Meta:
        model = CaseNote
        fields = [
            'id', 'note_code', 'patientId', 'ownerName', 'animal', 'date',
            'vetName', 'diagnosis', 'treatment', 'followUpDate', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'note_code', 'created_at', 'updated_at']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['id'] = instance.note_code if instance.note_code else str(instance.id)
        if instance.patient:
            ret['patientId'] = instance.patient.patient_code
        return ret
