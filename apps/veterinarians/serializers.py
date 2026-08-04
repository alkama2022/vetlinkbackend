from rest_framework import serializers
from .models import VeterinarianProfile


class VeterinarianSerializer(serializers.ModelSerializer):
    class Meta:
        model = VeterinarianProfile
        fields = [
            'id', 'vet_code', 'full_name', 'license_number', 'qualifications',
            'specializations', 'species_treated', 'diseases_expertise',
            'years_experience', 'languages', 'clinic_name', 'clinic_address',
            'lga', 'service_area', 'whatsapp_number', 'phone', 'email',
            'available', 'available_online', 'available_emergency',
            'consultation_fee', 'rating', 'total_consultations', 'bio',
            'avatar_initials', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class VetMatchRequestSerializer(serializers.Serializer):
    species = serializers.CharField(required=False, allow_blank=True)
    diseaseName = serializers.CharField(required=False, allow_blank=True)
    symptomsEn = serializers.CharField(required=False, allow_blank=True)
    farmerLga = serializers.CharField(required=False, allow_blank=True)
