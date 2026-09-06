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


def get_client_ip(request):
    """Return the caller's IP, honouring proxy headers only when configured to."""
    remote_addr = request.META.get('REMOTE_ADDR') or UNKNOWN_IP

    if not getattr(settings, 'TRUST_X_FORWARDED_FOR', False):
        return remote_addr

    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    chain = [part.strip() for part in forwarded.split(',') if part.strip()]
    if not chain:
        return request.META.get('HTTP_X_REAL_IP', '').strip() or remote_addr

    # With N trusted proxies in front of us, chain[-N] is the address the
    # outermost trusted proxy observed. Anything further left is client-supplied.
    depth = max(1, int(getattr(settings, 'TRUSTED_PROXY_COUNT', 1)))
    index = max(0, len(chain) - depth)
    return chain[index]


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
