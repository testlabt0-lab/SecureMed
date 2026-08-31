"""
Serializers for patients app.
"""
from rest_framework import serializers
from apps.patients.models import Patient, MedicalRecord, Medication, MedicationLog


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


class MedicationSerializer(serializers.ModelSerializer):
    """Serializer for Medication plans (mobile medication reminders)."""

    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    prescribed_by_name = serializers.CharField(
        source='prescribed_by.full_name', read_only=True
    )
    channel_name = serializers.CharField(
        source='channel.name', read_only=True, default=''
    )
    times = serializers.ListField(
        child=serializers.CharField(), read_only=True
    )
    is_scheduled_today = serializers.BooleanField(read_only=True)

    class Meta:
        model = Medication
        fields = [
            'id', 'patient', 'patient_name', 'channel', 'channel_name',
            'name', 'dosage', 'dose_times', 'times', 'start_date', 'end_date',
            'instructions', 'prescribed_by', 'prescribed_by_name',
            'is_active', 'is_scheduled_today', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'prescribed_by', 'created_at', 'updated_at']

    def validate_dose_times(self, value):
        import datetime as _dt
        parts = [p.strip() for p in (value or '').split(',') if p.strip()]
        if not parts:
            raise serializers.ValidationError('أدخل وقت جرعة واحد على الأقل بصيغة HH:MM')
        for part in parts:
            try:
                _dt.datetime.strptime(part, '%H:%M')
            except ValueError:
                raise serializers.ValidationError(
                    f'صيغة وقت غير صالحة: {part} — المطلوب HH:MM'
                )
        return ','.join(parts)

    def validate(self, attrs):
        start = attrs.get('start_date')
        end = attrs.get('end_date')
        if start and end and end < start:
            raise serializers.ValidationError(
                {'end_date': 'تاريخ الانتهاء يجب أن يكون بعد تاريخ البدء'}
            )
        return attrs

    def create(self, validated_data):
        validated_data['prescribed_by'] = self.context['request'].user
        return Medication.objects.create(**validated_data)


class MedicationLogSerializer(serializers.ModelSerializer):
    """Serializer for dose adherence logs."""

    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    medication_name = serializers.CharField(
        source='medication.name', read_only=True
    )
    recorded_by_name = serializers.CharField(
        source='recorded_by.full_name', read_only=True, default=''
    )

    class Meta:
        model = MedicationLog
        fields = [
            'id', 'medication', 'medication_name', 'scheduled_for',
            'status', 'status_display', 'taken_at', 'notes',
            'recorded_by', 'recorded_by_name', 'created_at',
        ]
        read_only_fields = ['id', 'taken_at', 'recorded_by', 'created_at']
