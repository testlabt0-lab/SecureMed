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
        request = self.context.get('request')

        if email and password:
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                # Log failed attempt with invalid email
                if request:
                    from apps.accounts.models import LoginAttempt
                    LoginAttempt.log_attempt(
                        request=request,
                        success=False,
                        email=email,
                        failure_reason='INVALID_EMAIL',
                        auth_method='PASSWORD',
                    )
                raise serializers.ValidationError(
                    {'detail': 'بيانات الاعتماد غير صحيحة'}
                )

            if not user.is_active:
                # Log failed attempt with disabled account
                if request:
                    from apps.accounts.models import LoginAttempt
                    LoginAttempt.log_attempt(
                        request=request,
                        success=False,
                        email=email,
                        user=user,
                        failure_reason='ACCOUNT_DISABLED',
                        auth_method='PASSWORD',
                    )
                raise serializers.ValidationError(
                    {'detail': 'هذا الحساب معطل — اتصل بمدير النظام'}
                )

            if user.is_locked:
                # Log failed attempt with locked account
                if request:
                    from apps.accounts.models import LoginAttempt
                    LoginAttempt.log_attempt(
                        request=request,
                        success=False,
                        email=email,
                        user=user,
                        failure_reason='ACCOUNT_LOCKED',
                        auth_method='PASSWORD',
                    )
                raise serializers.ValidationError(
                    {'detail': f'الحساب مقفل حتى {user.locked_until}'}
                )

            if not user.check_password(password):
                user.failed_login_attempts += 1
                if user.failed_login_attempts >= 5:
                    user.lock_account()
                user.save()
                
                # Log failed login attempt
                if request:
                    from apps.accounts.models import LoginAttempt
                    device_fp = getattr(request, 'device_fp', None)
                    LoginAttempt.log_attempt(
                        request=request,
                        success=False,
                        email=email,
                        user=user,
                        failure_reason='INVALID_PASSWORD',
                        auth_method='PASSWORD',
                        device_fp=device_fp,
                    )
                
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

    Modern flow: the mobile app generates an EC key pair inside the
    Android Keystore (biometric-gated) and submits the PUBLIC key here.
    At login the device signs a server challenge; the server verifies the
    signature with the stored public key. Raw biometric data never
    leaves the device.

    Legacy `biometric_template` is still accepted for old clients.
    """
    device_id = serializers.CharField(max_length=255)
    device_name = serializers.CharField(max_length=255, required=False)
    platform = serializers.ChoiceField(choices=['ANDROID', 'IOS', 'WEB'])
    public_key = serializers.CharField(write_only=True, required=False)
    biometric_template = serializers.CharField(write_only=True, required=False)

    def validate(self, attrs):
        if not attrs.get('public_key') and not attrs.get('biometric_template'):
            raise serializers.ValidationError(
                {'detail': 'المفتاح العام (public_key) مطلوب لتسجيل البصمة'}
            )
        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        salt = secrets.token_hex(32)
        public_key = validated_data.get('public_key', '')
        template = validated_data.get('biometric_template', public_key)
        biometric_hash = hash_biometric(template, salt)

        profile, created = BiometricProfile.objects.update_or_create(
            user=user,
            device_id=validated_data['device_id'],
            defaults={
                'device_name': validated_data.get('device_name', ''),
                'platform': validated_data['platform'],
                'biometric_hash': encrypt_field(biometric_hash),
                'salt': salt,
                'public_key': encrypt_field(public_key) if public_key else '',
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
    Verify biometric login by signature.
    Returns JWT tokens on success.

    Modern flow: client signs the challenge bytes with the private key
    stored in the Android Keystore (unlocked by the fingerprint), and
    sends the base64 signature. The server verifies it against the
    enrolled public key — a real biometric-bound proof of possession.

    Legacy `biometric_template` matching is kept for old clients.
    """
    challenge_id = serializers.UUIDField()
    signature = serializers.CharField(write_only=True, required=False)
    biometric_response = serializers.CharField(write_only=True, required=False)
    biometric_template = serializers.CharField(write_only=True, required=False)

    def validate(self, attrs):
        try:
            challenge = BiometricChallenge.objects.get(id=attrs['challenge_id'])
        except BiometricChallenge.DoesNotExist:
            raise serializers.ValidationError({'detail': 'التحدي غير صالح'})

        if not challenge.is_valid:
            raise serializers.ValidationError({'detail': 'انتهت صلاحية التحدي'})

        user = challenge.user

        # The user may have several enrolled devices — try each active
        # profile (get() would crash with MultipleObjectsReturned).
        profiles = list(
            BiometricProfile.objects.filter(user=user, is_active=True)
        )
        if not profiles:
            raise serializers.ValidationError({'detail': 'الملف البيوميتري غير موجود'})

        profile = None
        error_detail = 'فشل التحقق البيوميتري'
        signature_b64 = attrs.get('signature')
        template = attrs.get('biometric_template')

        if signature_b64:
            profile = _verify_signature(
                profiles, challenge.challenge, signature_b64
            )
            error_detail = 'التوقيع البيوميتري غير صالح'
        elif template:
            error_detail = 'البصمة غير مطابقة'
            for candidate in profiles:
                stored_hash = decrypt_field(candidate.biometric_hash)
                provided_hash = hash_biometric(template, candidate.salt)
                if secrets.compare_digest(stored_hash, provided_hash):
                    profile = candidate
                    break
        else:
            error_detail = 'التوقيع البيوميتري مطلوب (signature أو biometric_template)'

        if profile is None:
            first = profiles[0]
            first.failed_attempts += 1
            first.save()
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= 5:
                user.lock_account()
            user.save()
            raise serializers.ValidationError({'detail': error_detail})

        challenge.mark_used()
        profile.last_used = timezone.now()
        profile.failed_attempts = 0
        profile.save()
        user.reset_failed_attempts()

        attrs['user'] = user
        return attrs


def _verify_signature(profiles, challenge_text, signature_b64):
    """
    Verify a base64 ECDSA-SHA256 signature over the challenge bytes
    against the stored public key of each active profile.
    The stored key may be PEM or raw base64 DER (SubjectPublicKeyInfo).
    Returns the matching profile or None.
    """
    import base64 as _base64
    from cryptography.hazmat.primitives import hashes as _hashes
    from cryptography.hazmat.primitives.asymmetric import ec as _ec
    from cryptography.hazmat.primitives import serialization as _serialization
    from cryptography.exceptions import InvalidSignature

    try:
        signature_bytes = _base64.b64decode(signature_b64)
    except Exception:
        return None

    challenge_bytes = challenge_text.encode('utf-8')
    for candidate in profiles:
        stored = candidate.public_key
        if not stored:
            continue
        try:
            pem = decrypt_field(stored)
            if '-----BEGIN' in pem:
                public_key = _serialization.load_pem_public_key(pem.encode('utf-8'))
            else:
                public_key = _serialization.load_der_public_key(
                    _base64.b64decode(pem)
                )
            public_key.verify(
                signature_bytes,
                challenge_bytes,
                _ec.ECDSA(_hashes.SHA256()),
            )
            return candidate
        except InvalidSignature:
            continue
        except Exception:
            continue
    return None


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
