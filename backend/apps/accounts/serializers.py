"""
Serializers for accounts app.
"""
import secrets
import hashlib
from rest_framework import serializers
from django.contrib.auth import authenticate, password_validation
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User, BiometricProfile, BiometricChallenge
from apps.security.crypto import (
    encrypt_field, decrypt_field, hash_biometric,
    generate_challenge, verify_challenge
)


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model."""
    basin_name = serializers.CharField(source='basin.name', read_only=True, default='')

    class Meta:
        model = User
        fields = [
            'id', 'email', 'full_name', 'phone', 'role',
            'license_number', 'department', 'specialization',
            'basin', 'basin_name',
            'is_active',
            'is_biometric_enabled', 'mfa_enabled', 'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'mfa_enabled']


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new users (admin only)."""
    password = serializers.CharField(write_only=True, required=True)
    password_confirm = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = [
            'email', 'full_name', 'phone', 'role',
            'license_number', 'department', 'specialization',
            'basin',
            'password', 'password_confirm',
        ]

    def validate_password(self, value):
        try:
            password_validation.validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError(
                {'password_confirm': _('كلمتا المرور غير متطابقتين')}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User.objects.create_user(password=password, **validated_data)
        return user


class LoginSerializer(serializers.Serializer):
    """Serializer for email+password login."""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                raise serializers.ValidationError(
                    {'detail': 'بيانات الاعتماد غير صحيحة'}
                )

            if user.is_locked:
                # Provide user-friendly localized time format or time remaining
                import humanize
                import datetime
                from django.utils import timezone
                
                now = timezone.now()
                if user.locked_until > now:
                    delta = user.locked_until - now
                    minutes = int(delta.total_seconds() / 60)
                    raise serializers.ValidationError(
                        {'detail': f'تم قفل الحساب مؤقتًا لدواع أمنية. يرجى المحاولة بعد {minutes} دقيقة.'}
                    )
                else:
                    # Lock has expired, reset it
                    user.reset_failed_attempts()

            if not user.check_password(password):
                user.failed_login_attempts += 1
                if user.failed_login_attempts >= 3:
                    user.lock_account()
                user.save()
                raise serializers.ValidationError(
                    {'detail': 'بيانات الاعتماد غير صحيحة'}
                )

            user.reset_failed_attempts()
            attrs['user'] = user
            return attrs
        raise serializers.ValidationError(
            {'detail': 'يجب إدخال البريد الإلكتروني وكلمة المرور'}
        )


class BiometricEnrollSerializer(serializers.Serializer):
    """
    Serializer for enrolling biometric authentication.
    Security requirement #4: تسجيل الدخول بالبصمة
    """
    device_id = serializers.CharField(max_length=255)
    device_name = serializers.CharField(max_length=255, required=False)
    platform = serializers.ChoiceField(choices=['ANDROID', 'IOS', 'WEB'])
    biometric_template = serializers.CharField(write_only=True)

    def create(self, validated_data):
        user = self.context['request'].user
        salt = secrets.token_hex(32)
        biometric_hash = hash_biometric(validated_data['biometric_template'], salt)

        # Generate challenge keys
        challenge, expected_response = generate_challenge()

        profile, created = BiometricProfile.objects.update_or_create(
            user=user,
            device_id=validated_data['device_id'],
            defaults={
                'device_name': validated_data.get('device_name', ''),
                'platform': validated_data['platform'],
                'biometric_hash': encrypt_field(biometric_hash),
                'salt': salt,
                'is_active': True,
            }
        )

        user.is_biometric_enabled = True
        user.biometric_enrolled_at = timezone.now()
        user.save()

        return profile


class BiometricChallengeSerializer(serializers.Serializer):
    """Request a biometric challenge for login."""

    email = serializers.EmailField()
    device_id = serializers.CharField(max_length=255)

    def validate(self, attrs):
        try:
            user = User.objects.get(email=attrs['email'])
        except User.DoesNotExist:
            raise serializers.ValidationError({'detail': 'المستخدم غير موجود'})

        if not user.is_biometric_enabled:
            raise serializers.ValidationError(
                {'detail': 'المصادقة البيومترية غير مفعلة لهذا الحساب'}
            )

        try:
            profile = BiometricProfile.objects.get(
                user=user, device_id=attrs['device_id'], is_active=True
            )
        except BiometricProfile.DoesNotExist:
            raise serializers.ValidationError(
                {'detail': 'الجهاز غير مسجل للمصادقة البيومترية'}
            )

        if user.is_locked:
            raise serializers.ValidationError(
                {'detail': f'الحساب مقفل حتى {user.locked_until}'}
            )

        attrs['user'] = user
        attrs['profile'] = profile
        return attrs

    def create(self, validated_data):
        user = validated_data['user']
        challenge, expected_response = generate_challenge()

        from django.conf import settings
        ttl = settings.BIOMETRIC_SETTINGS['CHALLENGE_TTL_SECONDS']

        biometric_challenge = BiometricChallenge.objects.create(
            user=user,
            challenge=challenge,
            expected_response=encrypt_field(expected_response),
            expires_at=timezone.now() + timezone.timedelta(seconds=ttl),
        )
        return {
            'challenge_id': str(biometric_challenge.id),
            'challenge': challenge,
        }


class BiometricLoginSerializer(serializers.Serializer):
    """
    Verify biometric login response.
    Returns JWT tokens on success.
    """
    challenge_id = serializers.UUIDField()
    biometric_response = serializers.CharField(write_only=True)
    biometric_template = serializers.CharField(write_only=True)

    def validate(self, attrs):
        try:
            challenge = BiometricChallenge.objects.get(id=attrs['challenge_id'])
        except BiometricChallenge.DoesNotExist:
            raise serializers.ValidationError({'detail': 'التحدي غير صالح'})

        if not challenge.is_valid:
            raise serializers.ValidationError({'detail': 'انتهت صلاحية التحدي'})

        user = challenge.user

        # Verify biometric
        try:
            profile = BiometricProfile.objects.get(
                user=user, is_active=True
            )
        except BiometricProfile.DoesNotExist:
            raise serializers.ValidationError({'detail': 'الملف البيوميتري غير موجود'})

        # Verify the biometric template matches stored hash
        stored_hash = decrypt_field(profile.biometric_hash)
        provided_hash = hash_biometric(attrs['biometric_template'], profile.salt)

        if not secrets.compare_digest(stored_hash, provided_hash):
            profile.failed_attempts += 1
            profile.save()
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= 5:
                user.lock_account()
            user.save()
            raise serializers.ValidationError({'detail': 'البصمة غير مطابقة'})

        # Verify challenge response
        expected = decrypt_field(challenge.expected_response)
        if not verify_challenge(expected, attrs['biometric_response']):
            raise serializers.ValidationError({'detail': 'فشل التحقق من الاستجابة'})

        challenge.mark_used()
        profile.last_used = timezone.now()
        profile.failed_attempts = 0
        profile.save()
        user.reset_failed_attempts()

        attrs['user'] = user
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change."""
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('كلمة المرور القديمة غير صحيحة')
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'كلمتا المرور غير متطابقتين'})
        try:
            password_validation.validate_password(attrs['new_password'])
        except ValidationError as e:
            raise serializers.ValidationError({'new_password': list(e.messages)})
        return attrs

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


# ---------------------------------------------------------------------------
# Password reset (forgot password) — anonymous flow, see accounts/views.py
# ---------------------------------------------------------------------------
class PasswordResetRequestSerializer(serializers.Serializer):
    """Email body for POST /auth/password/reset/ (anonymous)."""
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Body for POST /auth/password/reset/confirm/ (uid + token + new password)."""
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'كلمتا المرور غير متطابقتين'})
        try:
            password_validation.validate_password(attrs['new_password'])
        except ValidationError as e:
            raise serializers.ValidationError({'new_password': list(e.messages)})
        return attrs
