import logging
from django.utils import timezone
from django.core.cache import cache
from apps.security.models import DeviceRegistry
from apps.audit.utils import log_security_event

logger = logging.getLogger('security')


class DeviceTracker:
    """
    Tracks and registers devices for users.
    Detects new devices and suspicious activities.
    """

    @staticmethod
    def track_device(user, request, device_info):
        """
        Track the current device for the user.
        Args:
            user: User object
            request: Django request
            device_info: Dictionary containing mac_address, device_fingerprint, os_info, etc.
        """
        if not user or not user.is_authenticated:
            return

        fingerprint = device_info.get('device_fingerprint')
        if not fingerprint:
            return

        # Check if device is already registered for this user
        device, created = DeviceRegistry.objects.update_or_create(
            user=user,
            device_fingerprint=fingerprint,
            defaults={
                'mac_address': device_info.get('mac_address', ''),
                'os_info': device_info.get('os_info', ''),
                'browser_info': device_info.get('browser_info', ''),
                'last_ip_address': device_info.get('ip_address', ''),
                'last_login': timezone.now(),
            }
        )

        if created:
            # This is a new device for this user!
            logger.info(f"New device detected for user {user.id}: {fingerprint}")
            log_security_event(
                user=user,
                event_type='SUSPICIOUS_ACTIVITY', # Or maybe a new NEW_DEVICE_DETECTED event
                request=request,
                severity='WARNING',
                details={'reason': 'New device detected', 'device_fingerprint': fingerprint}
            )
            
            # Here we could also trigger an email notification
            # from utils.email_service import send_securemed_email
            # send_securemed_email(user.email, 'تنبيه: تسجيل دخول من جهاز جديد', ...)
            
        return device, created

    @staticmethod
    def is_device_blocked(fingerprint, mac_address=None):
        """Check if a device is blocked by fingerprint or MAC."""
        if not fingerprint and not mac_address:
            return False
            
        from apps.security.models import BlockedDevice
        
        # Check cache first for performance
        cache_key = f'blocked_device:{fingerprint}'
        is_blocked = cache.get(cache_key)
        
        if is_blocked is not None:
            return is_blocked
            
        # Check database
        query = BlockedDevice.objects.filter(is_active=True)
        if fingerprint and mac_address:
            is_blocked = query.filter(device_fingerprint=fingerprint).exists() or query.filter(mac_address=mac_address).exists()
        elif fingerprint:
            is_blocked = query.filter(device_fingerprint=fingerprint).exists()
        elif mac_address:
            is_blocked = query.filter(mac_address=mac_address).exists()
            
        # Cache result for 5 minutes
        cache.set(cache_key, is_blocked, 300)
        
        return is_blocked
