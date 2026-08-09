from rest_framework import serializers
from .models import LabSample


class LabSampleSerializer(serializers.ModelSerializer):
    dateReceived = serializers.CharField(source='date_received')
    patientId = serializers.CharField(source='patient_id_str', required=False, allow_blank=True)
    requestedBy = serializers.CharField(source='requested_by', required=False, allow_blank=True)
    resultFindings = serializers.CharField(source='result_findings', required=False, allow_blank=True)
    resultPositive = serializers.BooleanField(source='result_positive', required=False, allow_null=True)
    publishedAt = serializers.DateTimeField(source='published_at', read_only=True)

    class Meta:
        model = LabSample
        fields = [
            'id', 'sample_code', 'species', 'test', 'facility', 'status', 'priority',
            'dateReceived', 'patientId', 'requestedBy', 'resultFindings',
            'resultPositive', 'publishedAt', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'sample_code', 'publishedAt', 'created_at', 'updated_at']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['id'] = instance.sample_code if instance.sample_code else str(instance.id)
        return ret


class PublishResultSerializer(serializers.Serializer):
    findings = serializers.CharField()
    positive = serializers.BooleanField()
