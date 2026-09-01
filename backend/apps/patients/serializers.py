"""
Serializers for patients app.
"""
from rest_framework import serializers
from apps.patients.models import Patient, MedicalRecord


class PatientSerializer(serializers.ModelSerializer):
    """Serializer for Patient with encrypted fields."""

    full_name = serializers.CharField()
    national_id = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    emergency_contact = serializers.CharField(required=False, allow_blank=True)
    age = serializers.IntegerField(read_only=True)
    basin_name = serializers.CharField(source='basin.name', read_only=True, default='')

    class Meta:
        model = Patient
        fields = [
            'id', 'full_name', 'national_id', 'phone', 'address',
            'date_of_birth', 'gender', 'blood_type', 'height', 'weight',
            'allergies', 'chronic_conditions', 'current_medications',
            'emergency_contact', 'age',
            'basin', 'basin_name',
            'created_at',
        ]
        read_only_fields = ['id', 'age', 'created_at']

    def create(self, validated_data):
        # Use property setters for encryption
        patient = Patient(**validated_data)
        patient.save()
        return patient

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class MedicalRecordSerializer(serializers.ModelSerializer):
    """Serializer for MedicalRecord."""

    content = serializers.CharField()
    created_by_name = serializers.CharField(
        source='created_by.full_name', read_only=True
    )
    record_type_display = serializers.CharField(
        source='get_record_type_display', read_only=True
    )
    channel_name = serializers.CharField(source='channel.name', read_only=True)

    class Meta:
        model = MedicalRecord
        fields = [
            'id', 'channel', 'channel_name', 'record_type', 'record_type_display', 'title',
            'content', 'created_by', 'created_by_name',
            'blood_pressure_systolic', 'blood_pressure_diastolic',
            'heart_rate', 'temperature', 'respiratory_rate',
            'oxygen_saturation', 'is_critical',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        record = MedicalRecord(**validated_data)
        record.save()
        return record
