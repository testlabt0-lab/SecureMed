"""
Channel (Patient Case) models.

Implements:
- Visibility conditions (security requirement #1): user must be owner or member
- Permissions system (security requirement #2): grant, modify, revoke, remove
- DV requirement: each user has exactly ONE role per channel
"""
import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone
from django.conf import settings


class Channel(models.Model):
    """
    A Channel represents a patient case in SecureMed.

    Each channel has:
    - An owner (attending physician)
    - Members with specific roles (DV: ONE role per user per channel)
    - Visibility restrictions (only owner or members can see it)
    """

    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', _('نشط')
        ARCHIVED = 'ARCHIVED', _('مؤرشف')
        CLOSED = 'CLOSED', _('مغلق')

    class ChannelType(models.TextChoices):
        EMERGENCY = 'EMERGENCY', _('حالة طارئة')
        INPATIENT = 'INPATIENT', _('مريض مقيم')
        OUTPATIENT = 'OUTPATIENT', _('مريض خارجي')
        CONSULTATION = 'CONSULTATION', _('استشارة')
        FOLLOW_UP = 'FOLLOW_UP', _('متابعة')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('اسم القناة'), max_length=255)
    description = models.TextField(_('الوصف'), blank=True)
    channel_type = models.CharField(
        _('نوع القناة'), max_length=20,
        choices=ChannelType.choices, default=ChannelType.OUTPATIENT
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='owned_channels',
        verbose_name=_('مالك القناة')
    )

    # Patient reference
    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.CASCADE,
        related_name='channels',
        verbose_name=_('المريض')
    )

    # Basin linkage (plan requirement: cases are linked to a health basin)
    basin = models.ForeignKey(
        'basins.Basin', on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='channels', verbose_name=_('الحوض الصحي'),
    )

    status = models.CharField(
        _('الحالة'), max_length=10,
        choices=Status.choices, default=Status.ACTIVE
    )

    # Metadata
    is_encrypted = models.BooleanField(default=True)
    priority = models.CharField(
        _('الأولوية'), max_length=10,
        choices=[('LOW', 'منخفضة'), ('MEDIUM', 'متوسطة'),
                 ('HIGH', 'عالية'), ('URGENT', 'عاجلة')],
        default='MEDIUM'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _('قناة')
        verbose_name_plural = _('القنوات')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['owner']),
            models.Index(fields=['patient']),
        ]

    def __str__(self):
        return f'{self.name} ({self.get_channel_type_display()})'

    def can_view(self, user):
        """
        Security requirement #1: Visibility conditions
        User must be either the channel owner or a member.
        """
        if user.role in ['SUPER_ADMIN', 'HOSPITAL_ADMIN']:
            return True
        if self.owner_id == user.id:
            return True
        return self.memberships.filter(user=user, is_active=True).exists()

    def can_manage(self, user):
        """Check if user can manage the channel (grant/revoke permissions)."""
        if user.role in ['SUPER_ADMIN', 'HOSPITAL_ADMIN']:
            return True
        return self.owner_id == user.id

    def get_user_role(self, user):
        """
        DV requirement: each user has exactly ONE role per channel.
        Returns the user's role in this channel, or None.
        """
        if self.owner_id == user.id:
            return ChannelMembership.Role.OWNER
        membership = self.memberships.filter(user=user, is_active=True).first()
        return membership.role if membership else None

    def close(self):
        """Close the channel."""
        self.status = self.Status.CLOSED
        self.closed_at = timezone.now()
        self.save(update_fields=['status', 'closed_at'])


class ChannelMembership(models.Model):
    """
    Membership of a user in a channel.

    DV requirement: Each user has exactly ONE role per channel.
    Enforced by unique_together constraint.
    """

    class Role(models.TextChoices):
        OWNER = 'OWNER', _('مالك القناة')
        MODERATOR = 'MODERATOR', _('مشرف')
        EDITOR = 'EDITOR', _('محرر')
        CONTRIBUTOR = 'CONTRIBUTOR', _('مساهم')
        VIEWER = 'VIEWER', _('مشاهد')

    # Permission definitions per role
    ROLE_PERMISSIONS = {
        Role.OWNER: ['view', 'edit', 'delete', 'manage_members', 'manage_permissions', 'close'],
        Role.MODERATOR: ['view', 'edit', 'manage_content'],
        Role.EDITOR: ['view', 'edit', 'create_record'],
        Role.CONTRIBUTOR: ['view', 'create_record'],
        Role.VIEWER: ['view'],
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    channel = models.ForeignKey(
        Channel, on_delete=models.CASCADE,
        related_name='memberships',
        verbose_name=_('القناة')
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='channel_memberships',
        verbose_name=_('المستخدم')
    )
    role = models.CharField(
        _('الدور'), max_length=20,
        choices=Role.choices, default=Role.VIEWER
    )

    is_active = models.BooleanField(_('نشط'), default=True)
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='granted_memberships',
        verbose_name=_('مُ granted بواسطة')
    )

    notes = models.TextField(_('ملاحظات'), blank=True)
    expires_at = models.DateTimeField(_('تنتهي في'), null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('عضوية')
        verbose_name_plural = _('العضويات')
        # DV: ONE role per user per channel
        unique_together = ['channel', 'user']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['channel', 'user', 'is_active']),
            models.Index(fields=['user', 'is_active']),
        ]

    def __str__(self):
        return f'{self.user.full_name} - {self.channel.name} ({self.get_role_display()})'

    def clean(self):
        """Validate that user is medical staff (not a patient)."""
        if self.user.role == 'PATIENT':
            raise ValidationError(
                _('لا يمكن للمرضى أن يكونوا أعضاء في قنوات المرضى')
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def has_permission(self, permission):
        """Check if the membership role has a specific permission."""
        allowed = self.ROLE_PERMISSIONS.get(self.role, [])
        return permission in allowed

    def revoke(self, revoked_by=None):
        """Revoke membership (security requirement #2: سحب الصلاحية)."""
        self.is_active = False
        self.save(update_fields=['is_active', 'updated_at'])

    def change_role(self, new_role, changed_by=None):
        """
        Modify member's permissions (security requirement #2: تعديل الصلاحية).
        DV: User can only have ONE role per channel.
        """
        if new_role not in dict(self.Role.choices):
            raise ValidationError(_('دور غير صالح'))
        if new_role == self.Role.OWNER:
            raise ValidationError(_('لا يمكن تغيير الدور إلى مالك'))
        self.role = new_role
        self.save(update_fields=['role', 'updated_at'])


class ChannelMessage(models.Model):
    """
    In-channel secure message (medical case discussion).

    Only active channel members (or admins) can read/send messages.
    Every message is persisted for the case audit trail; edits are tracked.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    channel = models.ForeignKey(
        Channel, on_delete=models.CASCADE,
        related_name='messages',
        verbose_name=_('القناة')
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='channel_messages',
        verbose_name=_('المرسل')
    )
    body = models.TextField(_('نص الرسالة'), max_length=4000)
    is_edited = models.BooleanField(_('معدلة'), default=False)
    is_system = models.BooleanField(_('رسالة نظام'), default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('رسالة قناة')
        verbose_name_plural = _('رسائل القنوات')
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['channel', 'created_at']),
            models.Index(fields=['sender']),
        ]

    def __str__(self):
        return f'{self.sender.full_name} @ {self.channel.name}: {self.body[:40]}'


class ChannelInvitation(models.Model):
    """Pending invitation to join a channel."""

    class Status(models.TextChoices):
        PENDING = 'PENDING', _('معلق')
        ACCEPTED = 'ACCEPTED', _('مقبول')
        REJECTED = 'REJECTED', _('مرفوض')
        EXPIRED = 'EXPIRED', _('منتهي')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    channel = models.ForeignKey(
        Channel, on_delete=models.CASCADE,
        related_name='invitations'
    )
    invitee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='channel_invitations'
    )
    role = models.CharField(
        _('الدور المقترح'), max_length=20,
        choices=ChannelMembership.Role.choices,
        default=ChannelMembership.Role.VIEWER
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True,
        related_name='sent_invitations'
    )
    status = models.CharField(
        _('الحالة'), max_length=10,
        choices=Status.choices, default=Status.PENDING
    )
    message = models.TextField(_('رسالة'), blank=True)
    expires_at = models.DateTimeField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('دعوة')
        verbose_name_plural = _('الدعوات')
        ordering = ['-created_at']

    def is_expired(self):
        return self.expires_at < timezone.now()

    def accept(self):
        """Accept the invitation and create membership."""
        if self.is_expired():
            self.status = self.Status.EXPIRED
            self.save(update_fields=['status'])
            raise ValidationError(_('انتهت صلاحية الدعوة'))

        self.status = self.Status.ACCEPTED
        self.save(update_fields=['status'])

        # Create membership
        membership, created = ChannelMembership.objects.get_or_create(
            channel=self.channel,
            user=self.invitee,
            defaults={
                'role': self.role,
                'granted_by': self.invited_by,
                'is_active': True,
            }
        )
        if not created:
            membership.role = self.role
            membership.is_active = True
            membership.save()
        return membership
