"""
Telemedicine serializers.
"""
from rest_framework import serializers
from .models import Consultation, ChatMessage
from django.conf import settings

class ChatMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.full_name', read_only=True)
    sender_role = serializers.CharField(source='sender.role', read_only=True)
    
    class Meta:
        model = ChatMessage
        fields = ['id', 'consultation', 'sender', 'sender_name', 'sender_role', 'content', 'attachment', 'created_at']
        read_only_fields = ['id', 'sender', 'created_at']


class ConsultationSerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()
    doctor_name = serializers.CharField(source='doctor.full_name', read_only=True)
    messages = ChatMessageSerializer(many=True, read_only=True)
    
    class Meta:
        model = Consultation
        fields = [
            'id', 'patient', 'patient_name', 'doctor', 'doctor_name',
            'appointment', 'scheduled_time', 'status', 'room_id', 'join_url',
            'notes', 'diagnosis', 'started_at', 'ended_at', 'created_at', 'messages'
        ]
        read_only_fields = ['id', 'room_id', 'started_at', 'ended_at', 'created_at']

    def get_patient_name(self, obj):
        try:
            return obj.patient.full_name
        except Exception:
            return str(obj.patient_id)


class ConsultationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Consultation
        fields = ['patient', 'appointment', 'scheduled_time']

    def create(self, validated_data):
        # The doctor is usually the one creating the consultation, or it's created automatically
        return Consultation.objects.create(
            doctor=self.context['request'].user,
            **validated_data
        )
