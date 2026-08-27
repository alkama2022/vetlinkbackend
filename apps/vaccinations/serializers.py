from rest_framework import serializers
from .models import VaccineTemplate, VaccinationRecord


class VaccineTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = VaccineTemplate
        fields = ['id', 'species', 'vaccine_name', 'dose_number', 'age_days', 'interval_days', 'notes', 'is_active']
        read_only_fields = ['id']


class VaccinationRecordSerializer(serializers.ModelSerializer):
    recordCode = serializers.CharField(source='record_code', read_only=True)
    animalName = serializers.CharField(source='animal_name')
    vaccineName = serializers.CharField(source='vaccine_name')
    doseNumber = serializers.IntegerField(source='dose_number')
    dateGiven = serializers.DateField(source='date_given')
    nextDueDate = serializers.DateField(source='next_due_date', allow_null=True)
    administeredBy = serializers.CharField(source='administered_by', required=False, allow_blank=True)
    batchNumber = serializers.CharField(source='batch_number', required=False, allow_blank=True)
    reminderSent = serializers.BooleanField(source='reminder_sent', read_only=True)

    class Meta:
        model = VaccinationRecord
        fields = [
            'id', 'recordCode', 'animalName', 'species', 'vaccineName',
            'doseNumber', 'dateGiven', 'nextDueDate', 'administeredBy',
            'batchNumber', 'notes', 'reminderSent', 'created_at',
        ]
        read_only_fields = ['id', 'recordCode', 'reminderSent', 'created_at']


class VaccinationCalendarSerializer(serializers.ModelSerializer):
    """Upcoming vaccination event for calendar view."""
    dueDate = serializers.DateField(source='next_due_date')
    animalName = serializers.CharField(source='animal_name')
    vaccineName = serializers.CharField(source='vaccine_name')

    class Meta:
        model = VaccinationRecord
        fields = ['id', 'animalName', 'vaccineName', 'doseNumber', 'dueDate']
