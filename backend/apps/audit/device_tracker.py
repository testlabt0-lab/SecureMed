import logging 
from django .utils import timezone 
from django .core .cache import cache 
from apps .security .models import DeviceRegistry 
from apps .audit .utils import log_security_event 

logger =logging .getLogger ('security')


class DeviceTracker :
    """
    Tracks and registers devices for users.
    Detects new devices and suspicious activities.
    """

    @staticmethod 
    def track_device (user ,request ,device_info ):
        """
        Track the current device for the user.
        Args:
            user: User object
            request: Django request
            device_info: Dictionary containing mac_address, device_fingerprint, os_info, etc.
        """
        if not user or not user .is_authenticated :
            return None ,False 

        fingerprint = device_info.get('device_fingerprint')
        if not fingerprint:
            return None, False

        ip_address = device_info.get('ip_address', '')
        location = ''
        if ip_address and ip_address not in ('127.0.0.1', '::1', 'localhost'):
            try:
                import requests
                # Use ip-api for location tracking (with timeout to avoid hanging)
                response = requests.get(f'http://ip-api.com/json/{ip_address}', timeout=2)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('status') == 'success':
                        location = f"{data.get('city', '')}, {data.get('country', '')}".strip(', ')
            except Exception as e:
                logger.warning(f"Could not fetch location for IP {ip_address}: {e}")

        existing_device = DeviceRegistry.objects.filter(user=user, device_fingerprint=fingerprint).first()
        is_new_location = False
        if existing_device and existing_device.location and location:
            if existing_device.location != location:
                is_new_location = True

            # Comment_111
        device, created = DeviceRegistry.objects.update_or_create(
            user=user,
            device_fingerprint=fingerprint,
            defaults={
                'mac_address': device_info.get('mac_address', ''),
                'os_info': device_info.get('os_info', ''),
                'browser_info': device_info.get('browser_info', ''),
                'last_ip_address': ip_address,
                'location': location if location else (existing_device.location if existing_device else ''),
                'last_login': timezone.now(),
            }
        )

        is_suspicious = created or is_new_location

        if is_suspicious:
        # Comment_112
            reason_msg = "New location detected" if is_new_location else "New device detected"
            logger.info(f"{reason_msg} for user {user.id}: {fingerprint} at {location}")
            log_security_event(
                user=user,
                event_type='SUSPICIOUS_ACTIVITY',# Comment_113
                request=request,
                severity='WARNING',
                details={'reason': reason_msg, 'device_fingerprint': fingerprint, 'location': location}
            )

        return device, is_suspicious

    @staticmethod 
    def is_device_blocked (fingerprint ,mac_address =None ):
        """Check if a device is blocked by fingerprint or MAC."""
        if not fingerprint and not mac_address :
            return False 

        from apps .security .models import BlockedDevice 

        # Comment_117
        cache_key =f'blocked_device:{fingerprint }'
        is_blocked =cache .get (cache_key )

        if is_blocked is not None :
            return is_blocked 

            # Comment_118
        query =BlockedDevice .objects .filter (is_active =True )
        if fingerprint and mac_address :
            is_blocked =query .filter (device_fingerprint =fingerprint ).exists ()or query .filter (mac_address =mac_address ).exists ()
        elif fingerprint :
            is_blocked =query .filter (device_fingerprint =fingerprint ).exists ()
        elif mac_address :
            is_blocked =query .filter (mac_address =mac_address ).exists ()

            # Comment_119
        cache .set (cache_key ,is_blocked ,300 )

        return is_blocked 
