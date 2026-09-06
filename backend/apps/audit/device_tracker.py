import ipaddress
import logging
from django .conf import settings
from django .utils import timezone
from django .core .cache import cache
from apps .security .models import DeviceRegistry
from apps .audit .utils import log_security_event

logger =logging .getLogger ('security')

GEOLOCATION_CACHE_TTL =60 *60 *24


def _geolocate (ip_address ):
    """Best-effort city/country for ``ip_address``; '' when unavailable.

    This used to run unconditionally on **every login**: a blocking
    ``requests.get('http://ip-api.com/json/<ip>', timeout=2)`` inside the login
    request. Three problems, in order of seriousness:

    1. It disclosed every user's IP to an unaffiliated third party over plaintext
       HTTP — no consent, no DPA, and observable in transit. In a system holding
       medical records that is a hard thing to justify for a label on a device
       row, so the call is now opt-in via ``GEOIP_LOOKUP_ENABLED``.
    2. It put up to two seconds of third-party network latency on the critical
       path of authentication, and ip-api being slow made logging in slow.
    3. Only the loopback addresses were excluded, so private ranges
       (``192.168.0.0/16``) and the documentation ranges used in tests were sent
       out too, which is both pointless and slow.

    Results are cached per IP: location changes far more slowly than users log
    in, and ip-api's free tier is rate-limited per source address.
    """
    if not getattr (settings ,'GEOIP_LOOKUP_ENABLED',False ):
        return ''
    if not ip_address :
        return ''
    try :
        if not ipaddress .ip_address (ip_address ).is_global :
            return ''
    except ValueError :
        return ''

    cache_key =f'geoip:{ip_address }'
    cached =cache .get (cache_key )
    if cached is not None :
        return cached

    location =''
    try :
        import requests
        endpoint =getattr (settings ,'GEOIP_LOOKUP_URL','https://ip-api.com/json/{ip}')
        response =requests .get (endpoint .format (ip =ip_address ),timeout =2 )
        if response .status_code ==200 :
            data =response .json ()
            if data .get ('status')=='success':
                location =f"{data .get ('city','')}, {data .get ('country','')}".strip (', ')
    except Exception as e :
        logger .warning (f"Could not fetch location for IP {ip_address }: {e }")
        return ''

    cache .set (cache_key ,location ,timeout =GEOLOCATION_CACHE_TTL )
    return location


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
        location = _geolocate(ip_address)

        existing_device = DeviceRegistry.objects.filter(user=user, device_fingerprint=fingerprint).first()
        is_new_location = False
        if existing_device and existing_device.location and location:
            if existing_device.location != location:
                is_new_location = True

            # Check if device is already registered for this user
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
        # This is a new device for this user!
            reason_msg = "New location detected" if is_new_location else "New device detected"
            logger.info(f"{reason_msg} for user {user.id}: {fingerprint} at {location}")
            log_security_event(
                user=user,
                event_type='SUSPICIOUS_ACTIVITY',# Or maybe a new NEW_DEVICE_DETECTED event
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

        # Check cache first for performance
        # Both identifiers go into the key. Keying on the fingerprint alone made
        # every MAC-only lookup share the single key 'blocked_device:', so one
        # blocked MAC blocked all of them.
        cache_key =f'blocked_device:{fingerprint }:{mac_address or ""}'
        is_blocked =cache .get (cache_key )

        if is_blocked is not None :
            return is_blocked 

            # Check database
        # enforceable(), not is_active=True: an expired temporary block must stop
        # counting as blocked (see apps.security.models.BlocklistQuerySet).
        query =BlockedDevice .objects .enforceable ()
        if fingerprint and mac_address :
            is_blocked =query .filter (device_fingerprint =fingerprint ).exists ()or query .filter (mac_address =mac_address ).exists ()
        elif fingerprint :
            is_blocked =query .filter (device_fingerprint =fingerprint ).exists ()
        elif mac_address :
            is_blocked =query .filter (mac_address =mac_address ).exists ()

            # Cache result for 5 minutes
        cache .set (cache_key ,is_blocked ,300 )

        return is_blocked 
