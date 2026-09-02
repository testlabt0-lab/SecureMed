"""
Serializers for the Appointments app.
"""
from rest_framework import serializers
from django.utils import timezone
from apps.appointments.models import Appointment, AppointmentSlot
from apps.accounts.serializers import UserSerializer
from apps.patients.serializers import PatientSerializer


class AppointmentSlotSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source='doctor.full_name', read_only=True)

    class Meta:
        model = AppointmentSlot
        fields = ['id', 'doctor', 'doctor_name', 'day_of_week', 'start_time',
                  'end_time', 'slot_duration_minutes', 'is_active']
        read_only_fields = ['id']


class AppointmentSerializer(serializers.ModelSerializer):
    """Full appointment serializer (read)."""
    patient_name = serializers.SerializerMethodField()
    patient_id_display = serializers.CharField(source='patient.national_id_display', read_only=True, default='')
    doctor_name = serializers.CharField(source='doctor.full_name', read_only=True)
    doctor_specialization = serializers.CharField(source='doctor.specialization', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True, default='')
    channel_name = serializers.CharField(source='channel.name', read_only=True, default='')
    basin_name = serializers.CharField(source='basin.name', read_only=True, default='')
    end_time = serializers.DateTimeField(read_only=True)
    is_past = serializers.BooleanField(read_only=True)
    is_upcoming = serializers.BooleanField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    type_display = serializers.CharField(source='get_appointment_type_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)

    class Meta:
        model = Appointment
        fields = [
            'id', 'patient', 'patient_name', 'patient_id_display',
            'doctor', 'doctor_name', 'doctor_specialization',
            'channel', 'channel_name', 'basin', 'basin_name',
            'created_by', 'created_by_name',
            'appointment_type', 'type_display',
            'priority', 'priority_display',
            'status', 'status_display',
            'scheduled_at', 'duration_minutes', 'end_time',
            'location', 'room_number',
            'is_virtual', 'virtual_link',
            'title', 'notes', 'instructions',
            'summary', 'follow_up_needed', 'follow_up_date',
            'cancellation_reason', 'cancelled_at',
            'is_past', 'is_upcoming',
            'reminder_sent_24h', 'reminder_sent_1h',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'created_by', 'cancelled_at', 'cancelled_by',
            'reminder_sent_24h', 'reminder_sent_1h', 'created_at', 'updated_at',
        ]

    def get_patient_name(self, obj):
        try:
            return obj.patient.full_name
        except Exception:
            return ''


class AppointmentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating appointments."""

    class Meta:
        model = Appointment
        fields = [
            'patient', 'doctor', 'channel', 'basin',
            'appointment_type', 'priority', 'status',
            'scheduled_at', 'duration_minutes',
            'location', 'room_number', 'is_virtual', 'virtual_link',
            'title', 'notes', 'instructions',
        ]

    def validate_scheduled_at(self, value):
        if value < timezone.now():
            raise serializers.ValidationError('لا يمكن جدولة موعد في الماضي.')
        return value

    def validate(self, attrs):
        """Check for doctor conflicts."""
        from datetime import timedelta
        doctor = attrs.get('doctor')
        scheduled_at = attrs.get('scheduled_at')
        duration = attrs.get('duration_minutes', 30)

        if doctor and scheduled_at:
            end = scheduled_at + timedelta(minutes=duration)
            qs = Appointment.objects.filter(
                doctor=doctor,
                status__in=[Appointment.Status.SCHEDULED, Appointment.Status.CONFIRMED],
                scheduled_at__lt=end,
            )
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            for appt in qs:
                if appt.end_time > scheduled_at:
                    raise serializers.ValidationError(
                        f'الطبيب لديه موعد آخر في هذا الوقت: «{appt.title}»'
                    )
        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['created_by'] = request.user
        return super().create(validated_data)


class AppointmentCompleteSerializer(serializers.Serializer):
    """Mark an appointment as completed."""
    summary = serializers.CharField(required=False, allow_blank=True)
    follow_up_needed = serializers.BooleanField(required=False, default=False)
    follow_up_date = serializers.DateField(required=False, allow_null=True)


class AppointmentCancelSerializer(serializers.Serializer):
    """Cancel an appointment."""
    reason = serializers.CharField(required=False, allow_blank=True, max_length=500)


class CalendarEventSerializer(serializers.ModelSerializer):
    """Compact serializer for calendar view."""
    title = serializers.SerializerMethodField()
    start = serializers.DateTimeField(source='scheduled_at')
    end = serializers.DateTimeField(source='end_time')
    color = serializers.SerializerMethodField()
    patient_name = serializers.SerializerMethodField()
    doctor_name = serializers.CharField(source='doctor.full_name', read_only=True)

    STATUS_COLORS = {
        'SCHEDULED': '#3b82f6',
        'CONFIRMED': '#10b981',
        'IN_PROGRESS': '#f59e0b',
        'COMPLETED': '#6b7280',
        'CANCELLED': '#ef4444',
        'NO_SHOW': '#dc2626',
        'RESCHEDULED': '#8b5cf6',
    }

    class Meta:
        model = Appointment
        fields = ['id', 'title', 'start', 'end', 'color', 'status',
                  'appointment_type', 'patient_name', 'doctor_name',
                  'location', 'is_virtual', 'priority']

    def get_title(self, obj):
        try:
            return f'{obj.get_appointment_type_display()} — {obj.patient.full_name}'
        except Exception:
            return obj.title

    def get_color(self, obj):
        return self.STATUS_COLORS.get(obj.status, '#3b82f6')

    def get_patient_name(self, obj):
        try:
            return obj.patient.full_name
        except Exception:
            return ''
