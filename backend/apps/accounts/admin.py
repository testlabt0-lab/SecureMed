from unfold.admin import ModelAdmin
"""
Admin configuration for accounts app.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from apps.accounts.models import User, BiometricProfile, BiometricChallenge


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'full_name', 'role', 'is_biometric_enabled', 'is_active')
    list_filter = ('role', 'is_active', 'is_biometric_enabled')
    search_fields = ('email', 'full_name', 'license_number')
    ordering = ('-created_at',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('المعلومات الشخصية', {
            'fields': ('full_name', 'phone', 'role', 'license_number',
                      'department', 'specialization')
        }),
        # `mfa_secret` used to be an editable field here. Reading it is pointless
        # (it is stored encrypted) but writing it is not: an admin could plant a TOTP
        # seed they control and quietly own a user's second factor, with no audit
        # event, since the API endpoints that log MFA_ENABLED/MFA_DISABLED are
        # bypassed entirely. What an operator actually needs is whether MFA is on and
        # since when, so that is what is shown — read only. Unlocking an account
        # (failed_login_attempts / locked_until) stays editable on purpose.
        ('الأمان', {
            'fields': ('is_biometric_enabled', 'biometric_enrolled_at',
                      'last_login_ip', 'failed_login_attempts', 'locked_until',
                      'mfa_enabled', 'mfa_created_at')
        }),
        ('الصلاحيات', {
            'fields': ('is_active', 'is_staff', 'is_superuser',
                      'groups', 'user_permissions')
        }),
        ('مهم', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'role', 'password1', 'password2'),
        }),
    )
    readonly_fields = ('last_login', 'date_joined', 'biometric_enrolled_at',
                       'mfa_enabled', 'mfa_created_at', 'last_login_ip')


@admin.register(BiometricProfile)
class BiometricProfileAdmin(ModelAdmin):
    list_display = ('user', 'device_name', 'platform', 'is_active', 'last_used')
    list_filter = ('platform', 'is_active')
    search_fields = ('user__email', 'user__full_name', 'device_id')
    readonly_fields = ('biometric_hash', 'salt', 'created_at', 'updated_at')


@admin.register(BiometricChallenge)
class BiometricChallengeAdmin(ModelAdmin):
    list_display = ('user', 'expires_at', 'used', 'created_at')
    list_filter = ('used',)
    readonly_fields = ('challenge', 'expected_response', 'created_at')
