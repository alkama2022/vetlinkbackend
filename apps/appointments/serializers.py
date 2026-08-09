from rest_framework import serializers
from .models import Appointment


class AppointmentSerializer(serializers.ModelSerializer):
    ownerName = serializers.CharField(source='owner_name')
    patientId = serializers.CharField(source='patient_id_str', required=False, allow_blank=True)

    class Meta:
        model = Appointment
        fields = [
            'id', 'appointment_code', 'time', 'date', 'patientId',
            'ownerName', 'animal', 'reason', 'notes', 'status',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'appointment_code', 'created_at', 'updated_at']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['id'] = instance.appointment_code if instance.appointment_code else str(instance.id)
        if instance.patient:
            ret['patientId'] = instance.patient.patient_code
        return ret
