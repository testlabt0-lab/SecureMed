"""
Admin for channels app.
"""
from django.contrib import admin
from apps.channels.models import Channel, ChannelMembership, ChannelInvitation


@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'patient', 'status', 'priority', 'created_at')
    list_filter = ('status', 'priority', 'channel_type')
    search_fields = ('name', 'description', 'owner__email', 'patient__full_name')
    readonly_fields = ('id', 'created_at', 'updated_at', 'closed_at')


@admin.register(ChannelMembership)
class ChannelMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'channel', 'role', 'is_active', 'created_at')
    list_filter = ('role', 'is_active')
    search_fields = ('user__email', 'channel__name')


@admin.register(ChannelInvitation)
class ChannelInvitationAdmin(admin.ModelAdmin):
    list_display = ('invitee', 'channel', 'role', 'status', 'created_at')
    list_filter = ('status', 'role')
    search_fields = ('invitee__email', 'channel__name')
