from rest_framework import serializers
from .models import DiseaseReport


class DiseaseReportSerializer(serializers.ModelSerializer):
    submittedAt = serializers.DateTimeField(source='submitted_at', read_only=True)
    farmerName = serializers.CharField(source='farmer_name', required=False, allow_blank=True)
    alertStatus = serializers.CharField(source='alert_status')

    class Meta:
        model = DiseaseReport
        fields = [
            'id', 'species', 'disease', 'affected', 'dead', 'signs', 'date',
            'location', 'lga', 'coords', 'notes', 'photos', 'submittedAt', 'farmerName',
            'alertStatus', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'submittedAt', 'created_at', 'updated_at']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['id'] = instance.report_code if instance.report_code else str(instance.id)
        request = self.context.get('request')
        if request and ret.get('photos'):
            ret['photos'] = [
                request.build_absolute_uri(p) if isinstance(p, str) and not p.startswith('http') else p
                for p in ret['photos']
            ]
        return ret


class ReportStatusUpdateSerializer(serializers.Serializer):
    alertStatus = serializers.ChoiceField(choices=DiseaseReport.AlertStatusChoices.choices)
