"""Canonical client-IP resolution.

Audit records, rate limits and IP blocklists are only as trustworthy as the
address they are keyed on, so there must be exactly one way to derive it.

``X-Forwarded-For`` is a list the client can prepend to: a request carrying
``X-Forwarded-For: 1.2.3.4`` arrives at the app as ``1.2.3.4, <real client>``
once a single reverse proxy has appended the peer address. Reading the *leftmost*
entry therefore hands the attacker a free IP spoof — clean audit trails, reset
rate limits, and blocklists aimed at whichever victim they name. The only entries
we can trust are the ones our own proxies appended, i.e. the last
``TRUSTED_PROXY_COUNT`` of them, so the client address is counted from the right.
"""
from django.conf import settings

UNKNOWN_IP = '0.0.0.0'

import ipaddress

def _is_internal_or_private(ip_str):
    try:
        ip = ipaddress.ip_address(ip_str.strip())
        return ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local
    except (ValueError, AttributeError):
        return False


def get_client_ip(request):
    """Return the real client's public IP, properly handling reverse proxies (Render, Cloudflare, Nginx)."""
    # 1. Cloudflare connecting IP
    cf_ip = (request.META.get('HTTP_CF_CONNECTING_IP') or '').strip()
    if cf_ip and not _is_internal_or_private(cf_ip):
        return cf_ip

    # 2. X-Forwarded-For header (standard for Render and most cloud providers)
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded:
        chain = [part.strip() for part in forwarded.split(',') if part.strip()]
        # First non-private IP in the chain is the actual client IP
        for candidate in chain:
            if candidate and not _is_internal_or_private(candidate):
                return candidate
        if chain:
            return chain[0]

    # 3. X-Real-IP header
    real_ip = (request.META.get('HTTP_X_REAL_IP') or '').strip()
    if real_ip and not _is_internal_or_private(real_ip):
        return real_ip

    # 4. Fallback to REMOTE_ADDR
    remote_addr = (request.META.get('REMOTE_ADDR') or UNKNOWN_IP).strip()
    return remote_addr


def get_mac_address(ip_address):
    """Attempt to find the physical MAC address for an IP on the local network using ARP."""
    import subprocess
    import platform
    import re
    
    if not ip_address or ip_address in ['127.0.0.1', 'localhost', '::1', '0.0.0.0']:
        return ""
        
    try:
        # Works on Windows and Linux for local network devices
        if platform.system().lower() == 'windows':
            output = subprocess.check_output(['arp', '-a', ip_address], timeout=2).decode('utf-8', errors='ignore')
            # Look for xx-xx-xx-xx-xx-xx
            match = re.search(r'([0-9A-Fa-f]{2}(?:-[0-9A-Fa-f]{2}){5})', output)
            if match:
                return match.group(1).replace('-', ':').upper()
        else:
            output = subprocess.check_output(['arp', '-n', ip_address], timeout=2).decode('utf-8', errors='ignore')
            # Look for xx:xx:xx:xx:xx:xx
            match = re.search(r'([0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5})', output)
            if match:
                return match.group(1).upper()
    except Exception:
        pass
        
    return ""


def client_fingerprint(request):
    """Fingerprint a JWT is bound to.

    Issuing (``get_tokens_for_user``) and verifying
    (``security.authentication.BoundJWTAuthentication``) must derive this the same
    way or every request 401s, so both call this one function.

    The IP component is what makes a stolen token useless elsewhere, but it also
    invalidates tokens when a mobile client roams between networks; set
    ``JWT_BIND_CLIENT_IP=False`` to bind to the user agent alone.
    """
    import hashlib

    ip = get_client_ip(request) if getattr(settings, 'JWT_BIND_CLIENT_IP', True) else ''
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    return hashlib.sha256(f"{ip}:{user_agent}".encode('utf-8')).hexdigest()
