"""
Serializers for channels app.
"""
from rest_framework import serializers
from django.utils import timezone
from apps.channels.models import Channel, ChannelMembership, ChannelInvitation, ChannelMessage
from apps.accounts.serializers import UserSerializer


class ChannelMembershipSerializer(serializers.ModelSerializer):
    """Serializer for channel membership."""

    user = UserSerializer(read_only=True)
    user_email = serializers.EmailField(write_only=True, required=False)
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = ChannelMembership
        fields = [
            'id', 'channel', 'user', 'user_email', 'role', 'role_display',
            'is_active', 'granted_by', 'notes', 'expires_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'channel', 'user', 'granted_by', 'created_at', 'updated_at']

    def create(self, validated_data):
        user_email = validated_data.pop('user_email', None)
        if not user_email:
            raise serializers.ValidationError({'user_email': 'مطلوب'})

        from apps.accounts.models import User
        try:
            user = User.objects.get(email=user_email)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                {'user_email': 'المستخدم غير موجود'}
            )

        # DV: Check user doesn't already have a role in this channel
        existing = ChannelMembership.objects.filter(
            channel=validated_data['channel'], user=user
        ).first()
        if existing:
            if existing.is_active:
                raise serializers.ValidationError(
                    {'detail': 'المستخدم لديه بالفعل دور في هذه القناة'}
                )
            existing.role = validated_data.get('role', existing.role)
            existing.is_active = True
            existing.save()
            return existing

        return ChannelMembership.objects.create(
            user=user,
            granted_by=self.context['request'].user,
            **validated_data
        )


class ChannelSerializer(serializers.ModelSerializer):
    """Serializer for Channel."""

    owner = UserSerializer(read_only=True)
    current_user_role = serializers.SerializerMethodField()
    members_count = serializers.IntegerField(source='memberships.count', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    channel_type_display = serializers.CharField(
        source='get_channel_type_display', read_only=True
    )
    basin_name = serializers.CharField(source='basin.name', read_only=True, default='')

    class Meta:
        model = Channel
        fields = [
            'id', 'name', 'description', 'channel_type',
            'channel_type_display', 'owner', 'patient', 'basin', 'basin_name',
            'status', 'status_display', 'priority', 'is_encrypted',
            'current_user_role', 'members_count',
            'created_at', 'updated_at', 'closed_at',
        ]
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at', 'closed_at']

    def get_current_user_role(self, obj):
        """DV: Return the single role of current user in this channel."""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        return obj.get_user_role(request.user)


class ChannelDetailSerializer(ChannelSerializer):
    """Detailed serializer with members list."""

    memberships = ChannelMembershipSerializer(many=True, read_only=True)

    class Meta(ChannelSerializer.Meta):
        fields = ChannelSerializer.Meta.fields + ['memberships']


class ChannelInvitationSerializer(serializers.ModelSerializer):
    """Serializer for channel invitations."""

    invitee = UserSerializer(read_only=True)
    invited_by = UserSerializer(read_only=True)
    invitee_email = serializers.EmailField(write_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = ChannelInvitation
        fields = [
            'id', 'channel', 'invitee', 'invitee_email', 'invited_by',
            'role', 'status', 'status_display', 'message', 'expires_at',
            'created_at',
        ]
        read_only_fields = [
            'id', 'invitee', 'invited_by', 'status',
            'created_at', 'expires_at',
        ]

    def create(self, validated_data):
        invitee_email = validated_data.pop('invitee_email')
        from apps.accounts.models import User
        try:
            invitee = User.objects.get(email=invitee_email)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                {'invitee_email': 'المستخدم غير موجود'}
            )

        expires_at = timezone.now() + timezone.timedelta(days=7)
        return ChannelInvitation.objects.create(
            invitee=invitee,
            invited_by=self.context['request'].user,
            expires_at=expires_at,
            **validated_data
        )


class ModifyRoleSerializer(serializers.Serializer):
    """Serializer for modifying member role."""
    role = serializers.ChoiceField(choices=ChannelMembership.Role.choices)


class GrantPermissionSerializer(serializers.Serializer):
    """Serializer for granting permission to a channel."""
    user_email = serializers.EmailField()
    role = serializers.ChoiceField(choices=ChannelMembership.Role.choices)
    notes = serializers.CharField(required=False, allow_blank=True)
    expires_at = serializers.DateTimeField(required=False)


class RevokePermissionSerializer(serializers.Serializer):
    """Serializer for revoking permission."""
    reason = serializers.CharField(required=False, allow_blank=True)


class ChannelMessageSerializer(serializers.ModelSerializer):
    """Serializer for in-channel chat messages."""

    sender_name = serializers.CharField(source='sender.full_name', read_only=True)
    sender_role = serializers.CharField(source='sender.role', read_only=True)
    sender_role_display = serializers.CharField(
        source='sender.get_role_display', read_only=True
    )

    class Meta:
        model = ChannelMessage
        fields = [
            'id', 'channel', 'sender', 'sender_name', 'sender_role',
            'sender_role_display', 'body', 'is_edited', 'is_system',
            'created_at',
        ]
        read_only_fields = [
            'id', 'channel', 'sender', 'sender_name', 'sender_role',
            'sender_role_display', 'is_edited', 'is_system', 'created_at',
        ]

    def validate_body(self, value):
        value = (value or '').strip()
        if not value:
            raise serializers.ValidationError('لا يمكن إرسال رسالة فارغة')
        return value
