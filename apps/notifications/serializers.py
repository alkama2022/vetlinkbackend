from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    createdAt = serializers.DateTimeField(source='created_at_override', read_only=True)

    class Meta:
        model = Notification
        fields = ['id', 'notif_code', 'title', 'body', 'tone', 'read', 'createdAt']
        read_only_fields = ['id', 'notif_code', 'createdAt']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['id'] = instance.notif_code if instance.notif_code else str(instance.id)
        return ret
