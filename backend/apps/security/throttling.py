"""
Throttling classes for sensitive / anonymous endpoints.
"""
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle


class BiometricRateThrottle(UserRateThrottle):
    """Throttle for biometric authentication endpoints."""
    scope = 'biometric'


class PasswordResetRateThrottle(AnonRateThrottle):
    """
    Throttle for password-reset endpoints (anonymous).

    Rate is set in settings.DEFAULT_THROTTLE_RATES['password_reset'].
    Strict on purpose: prevents email-bombing and brute-force token guessing.
    """
    scope = 'password_reset'


class LoginRateThrottle(AnonRateThrottle):
    """
    Throttle for login endpoints to prevent brute force attacks.
    """
    scope = 'login'
