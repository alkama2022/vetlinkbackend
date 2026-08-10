from rest_framework import serializers
from .models import DiseaseReport


class DiseaseReportSerializer(serializers.ModelSerializer):
    submittedAt = serializers.DateTimeField(source='submitted_at', read_only=True)
    farmerName = serializers.CharField(source='farmer_name', required=False, allow_blank=True)
    # alert_status is intentionally read-only here: it can only be changed by
    # government officers/admins through the dedicated `status` action.
    alertStatus = serializers.CharField(source='alert_status', read_only=True)
    lga = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = DiseaseReport
        fields = [
            'id', 'species', 'disease', 'affected', 'dead', 'signs', 'date',
            'location', 'lga', 'coords', 'notes', 'photos', 'submittedAt', 'farmerName',
            'alertStatus', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'photos', 'submittedAt', 'created_at', 'updated_at']

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

    # Allowed workflow transitions. Anything not listed here is rejected so
    # reports can't jump backwards or skip verification steps.
    _ALLOWED_TRANSITIONS = {
        'Suspected': ['Under investigation', 'Closed'],
        'Under investigation': ['Confirmed', 'Closed'],
        'Confirmed': ['Closed'],
        'Closed': ['Suspected'],
    }

    def validate(self, attrs):
        current = self.context.get('current_status')
        requested = attrs['alertStatus']
        if current is not None:
            allowed = self._ALLOWED_TRANSITIONS.get(current, ())
            if requested != current and requested not in allowed:
                raise serializers.ValidationError(
                    {'alertStatus': f'Status cannot change from "{current}" to "{requested}".'}
                )
        return attrs
