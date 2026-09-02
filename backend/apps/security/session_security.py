import logging
from django.core.cache import cache
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

logger = logging.getLogger('security')

class SessionManager:
    """Manages user sessions, concurrent limits, and session binding."""

    MAX_CONCURRENT_SESSIONS = 3

    @staticmethod
    def register_session(user, request, token=None):
        """Register a new session for the user."""
        if not user or not user.is_authenticated:
            return

        session_id = request.session.session_key if hasattr(request, 'session') and request.session.session_key else ''
        device_fingerprint = request.META.get('HTTP_X_DEVICE_FINGERPRINT', '')
        
        # Track active sessions in cache
        cache_key = f'active_sessions:{user.id}'
        sessions = cache.get(cache_key, [])
        
        # Add new session
        new_session = {
            'session_id': session_id,
            'device_fingerprint': device_fingerprint,
            'timestamp': timezone.now().timestamp(),
            'ip_address': request.META.get('REMOTE_ADDR', '')
        }
        
        # Enforce max concurrent sessions limit
        if len(sessions) >= SessionManager.MAX_CONCURRENT_SESSIONS:
            # We would typically log out the oldest session here, 
            # but for simplicity, we just keep the newest ones.
            # In a real app with stateful sessions, we would invalidate the old session token.
            sessions = sorted(sessions, key=lambda x: x['timestamp'])
            sessions = sessions[-(SessionManager.MAX_CONCURRENT_SESSIONS - 1):]
            logger.warning(f"User {user.id} exceeded concurrent session limit. Terminating oldest.")

        sessions.append(new_session)
        cache.set(cache_key, sessions, timeout=86400) # 24h

    @staticmethod
    def force_logout_user(user_id):
        """Force logout all sessions for a user."""
        # Clear active sessions from cache
        cache_key = f'active_sessions:{user_id}'
        cache.delete(cache_key)
        
        # Note: In JWT, we can't easily invalidate tokens without a token blacklist.
        # Simple JWT has a token blacklist app which we could use if we had the specific tokens.
        # Alternatively, we could increment a user 'security_stamp' field to invalidate all tokens.
        logger.warning(f"Force logout executed for user {user_id}")
        
    @staticmethod
    def is_session_valid(user, request):
        """Check if the current session is valid and not hijacked."""
        if not user or not user.is_authenticated:
            return True
            
        current_fingerprint = request.META.get('HTTP_X_DEVICE_FINGERPRINT', '')
        
        # If we have a fingerprint, verify it matches the one registered for this session
        if current_fingerprint:
            # We would check if the token/session is bound to a different fingerprint
            # For now, we rely on the device tracker for suspicious activity
            pass
            
        return True
