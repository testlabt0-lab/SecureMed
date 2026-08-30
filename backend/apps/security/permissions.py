"""
Permissions classes for SecureMed.
"""
from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    """Allow access only to admin users."""

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role in ['SUPER_ADMIN', 'HOSPITAL_ADMIN']
        )


class IsMedicalStaff(permissions.BasePermission):
    """Allow access to medical staff (doctors, nurses, etc.)."""

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.is_medical_staff
        )


class IsDoctor(permissions.BasePermission):
    """Allow access to doctors only."""

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == 'DOCTOR'
        )


class IsAuditor(permissions.BasePermission):
    """Allow access to security auditors."""

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == 'AUDITOR'
        )


class IsChannelOwnerOrAdmin(permissions.BasePermission):
    """Allow access to channel owners or admins."""

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.role in ['SUPER_ADMIN', 'HOSPITAL_ADMIN']:
            return True
        # Check if user is the owner of the channel
        if hasattr(obj, 'owner'):
            return obj.owner == user
        if hasattr(obj, 'channel'):
            return obj.channel.owner == user
        return False


class ReadOnlyOrAdmin(permissions.BasePermission):
    """Read access for all authenticated, write only for admins."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role in ['SUPER_ADMIN', 'HOSPITAL_ADMIN']
        )
