from rest_framework import serializers
from .models import ConsultationRequest, ChatMessage


class ChatMessageSerializer(serializers.ModelSerializer):
    senderName = serializers.CharField(source='sender_name')
    sentAt = serializers.DateTimeField(source='sent_at', read_only=True)
    mediaUrl = serializers.CharField(source='media_url', required=False, allow_null=True)
    mediaType = serializers.CharField(source='media_type', required=False, allow_null=True)

    class Meta:
        model = ChatMessage
        fields = ['id', 'sender', 'senderName', 'text', 'mediaUrl', 'mediaType', 'sentAt', 'read']
        read_only_fields = ['id', 'sentAt']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['id'] = instance.message_code if instance.message_code else str(instance.id)
        return ret


class ConsultationRequestSerializer(serializers.ModelSerializer):
    farmerName = serializers.CharField(source='farmer_name', required=False, allow_blank=True)
    farmLocation = serializers.CharField(source='farm_location', required=False, allow_blank=True)
    vetId = serializers.CharField(source='vet_id_str', required=False, allow_blank=True)
    vetName = serializers.CharField(source='vet_name', required=False, allow_blank=True)
    diseaseName = serializers.CharField(source='disease_name', required=False, allow_blank=True)
    symptomsEn = serializers.CharField(source='symptoms_en', required=False, allow_blank=True)
    symptomsHa = serializers.CharField(source='symptoms_ha', required=False, allow_blank=True)
    animalAge = serializers.CharField(source='animal_age')
    animalGender = serializers.CharField(source='animal_gender')
    affectedCount = serializers.IntegerField(source='affected_count')
    durationDays = serializers.IntegerField(source='duration_days')
    additionalNotes = serializers.CharField(source='additional_notes', required=False, allow_blank=True)
    photoUrls = serializers.JSONField(source='photo_urls', required=False)
    videoUrls = serializers.JSONField(source='video_urls', required=False)
    voiceUrls = serializers.JSONField(source='voice_urls', required=False)
    submittedAt = serializers.DateTimeField(source='submitted_at', read_only=True)
    acceptedAt = serializers.DateTimeField(source='accepted_at', required=False, allow_null=True)
    resolvedAt = serializers.DateTimeField(source='resolved_at', required=False, allow_null=True)
    messages = ChatMessageSerializer(many=True, read_only=True)

    class Meta:
        model = ConsultationRequest
        fields = [
            'id', 'farmerName', 'farmLocation', 'vetId', 'vetName', 'channel',
            'status', 'diseaseName', 'symptomsEn', 'symptomsHa', 'species',
            'breed', 'animalAge', 'animalGender', 'affectedCount', 'durationDays',
            'severity', 'additionalNotes', 'photoUrls', 'videoUrls', 'voiceUrls',
            'submittedAt', 'acceptedAt', 'resolvedAt', 'messages'
        ]
        read_only_fields = ['id', 'submittedAt', 'messages']

    def create(self, validated_data):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not validated_data.get('farmer_name') and user:
            validated_data['farmer_name'] = getattr(user, 'full_name', '')
        return super().create(validated_data)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['id'] = instance.consultation_code if instance.consultation_code else str(instance.id)
        if instance.vet:
            ret['vetId'] = instance.vet.vet_code
        return ret
