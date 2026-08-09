from rest_framework import serializers
from .models import FarmerHerd, FarmerReminder


class FarmerHerdSerializer(serializers.ModelSerializer):
    class Meta:
        model = FarmerHerd
        fields = ['id', 'herd_code', 'type', 'count', 'healthy', 'created_at', 'updated_at']
        read_only_fields = ['id', 'herd_code', 'created_at', 'updated_at']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['id'] = instance.herd_code if instance.herd_code else str(instance.id)
        return ret


class FarmerReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = FarmerReminder
        fields = ['id', 'reminder_code', 'title', 'date', 'tone', 'done', 'created_at', 'updated_at']
        read_only_fields = ['id', 'reminder_code', 'created_at', 'updated_at']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['id'] = instance.reminder_code if instance.reminder_code else str(instance.id)
        return ret
