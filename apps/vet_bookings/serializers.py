from rest_framework import serializers
from .models import VetAvailability, VetBooking


class VetAvailabilitySerializer(serializers.ModelSerializer):
    vetName = serializers.CharField(source='vet.user.get_full_name', read_only=True)

    class Meta:
        model = VetAvailability
        fields = ['id', 'vet', 'vetName', 'date', 'start_time', 'end_time', 'is_booked']
        read_only_fields = ['id', 'is_booked']


class VetBookingSerializer(serializers.ModelSerializer):
    bookingCode = serializers.CharField(source='booking_code', read_only=True)
    farmerName = serializers.CharField(source='farmer.get_full_name', read_only=True)
    vetName = serializers.CharField(source='vet.user.get_full_name', read_only=True)
    vetId = serializers.UUIDField(source='vet.id', read_only=True)
    date = serializers.DateField(source='availability.date', read_only=True)
    startTime = serializers.TimeField(source='availability.start_time', read_only=True)
    endTime = serializers.TimeField(source='availability.end_time', read_only=True)
    animalName = serializers.CharField(source='animal_name')
    consultationFee = serializers.DecimalField(source='consultation_fee', max_digits=10, decimal_places=2)

    class Meta:
        model = VetBooking
        fields = [
            'id', 'bookingCode', 'farmer', 'farmerName', 'vet', 'vetName', 'vetId',
            'date', 'startTime', 'endTime', 'animalName', 'species', 'reason',
            'status', 'notes', 'consultationFee', 'created_at',
        ]
        read_only_fields = ['id', 'bookingCode', 'farmer', 'status', 'created_at']
