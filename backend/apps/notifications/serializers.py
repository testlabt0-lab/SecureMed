"""
Notifications serializers.
"""
from rest_framework import serializers
from apps.notifications.models import (
    Notification, NotificationPreference, EmailLog
)
from apps.accounts.serializers import UserSerializer


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification."""
    recipient = UserSerializer(read_only=True)
    sender = UserSerializer(read_only=True)
    type_display = serializers.CharField(source='get_notification_type_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id', 'recipient', 'sender', 'notification_type', 'type_display',
            'priority', 'priority_display', 'title', 'message', 'data',
            'related_object_type', 'related_object_id',
            'is_read', 'read_at', 'is_email_sent', 'email_sent_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'recipient', 'sender', 'is_read', 'read_at',
            'is_email_sent', 'email_sent_at', 'created_at', 'updated_at',
        ]


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for NotificationPreference."""

    class Meta:
        model = NotificationPreference
        fields = [
            'id', 'user',
            'email_channel_updates', 'email_security_alerts', 'email_medical_records',
            'push_channel_updates', 'push_security_alerts', 'push_medical_records',
            'in_app_all', 'quiet_hours_start', 'quiet_hours_end',
        ]
        read_only_fields = ['id', 'user']
