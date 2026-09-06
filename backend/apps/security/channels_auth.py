"""JWT authentication for WebSocket handshakes.

Channels' ``AuthMiddlewareStack`` authenticates from the Django session cookie.
Neither client ever establishes a session — the React SPA and the Android app
authenticate every HTTP call with ``Authorization: Bearer <access>`` — so
``scope['user']`` was ``AnonymousUser`` on every single WebSocket handshake. Both
consumers were broken by it, in opposite directions:

* ``telemedicine.VideoCallConsumer`` closes anonymous connections, so video
  consultations could never be established from either client. The advertised
  telemedicine feature was signalling-dead.
* ``notifications.NotificationConsumer`` *accepted* them and then joined no
  group, so the socket stayed open forever and no notification was ever pushed
  through it. It also meant an unauthenticated client could hold sockets open.

Browsers cannot set request headers on a WebSocket handshake, so the token has to
arrive by one of three routes. In preference order:

1. ``Sec-WebSocket-Protocol: access_token, <jwt>`` — the header is under the
   client's control via ``new WebSocket(url, protocols)`` and is *not* recorded in
   access logs, browser history or ``Referer``.
2. The access-token cookie, when the deployment issues one.
3. ``?token=<jwt>`` in the query string — supported because some proxies strip
   unknown subprotocols, but discouraged: query strings are logged, and a logged
   access token is a credential at rest. A warning is emitted when it is used.

Every token goes through ``enforce_token_security``, the same denylist, binding
and hijack checks DRF applies to HTTP requests. A WebSocket that skipped them
would be a way to keep using a token that has been force-logged-out.
"""
import logging
from urllib.parse import parse_qs

from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.exceptions import TokenError

logger = logging.getLogger('security')

TOKEN_SUBPROTOCOL = 'access_token'


class _ScopeRequest:
    """Minimal request shim over an ASGI scope.

    ``client_fingerprint`` and ``SessionManager.reject_if_hijacked`` read
    ``request.META``, so the scope's headers are translated into the WSGI-style
    names those functions expect. Building this instead of loosening the shared
    checks keeps HTTP and WebSocket auth on one code path.
    """

    def __init__(self, scope):
        self.scope = scope
        self.META = self._build_meta(scope)
        self.headers = {}
        for raw_name, raw_value in scope.get('headers') or []:
            name = raw_name.decode('latin-1').lower()
            self.headers[name] = raw_value.decode('latin-1')

    @staticmethod
    def _build_meta(scope):
        meta = {}
        client = scope.get('client') or ()
        if client:
            meta['REMOTE_ADDR'] = client[0]

        for raw_name, raw_value in scope.get('headers') or []:
            name = raw_name.decode('latin-1').lower()
            value = raw_value.decode('latin-1')
            if name == 'host':
                meta['HTTP_HOST'] = value
            else:
                meta['HTTP_' + name.upper().replace('-', '_')] = value
        return meta

    def get(self, key, default=None):
        return self.META.get(key, default)


def _cookies(scope):
    """Parse the handshake Cookie header into a dict."""
    for raw_name, raw_value in scope.get('headers') or []:
        if raw_name.decode('latin-1').lower() != 'cookie':
            continue
        jar = {}
        for chunk in raw_value.decode('latin-1').split(';'):
            name, _, value = chunk.partition('=')
            if name.strip():
                jar[name.strip()] = value.strip()
        return jar
    return {}


def _subprotocol_token(scope):
    """Read the token from ``Sec-WebSocket-Protocol``.

    The client sends two protocols — a marker and the token itself — because the
    header has no other way to carry a value. Anything that is not exactly that
    pair is ignored rather than guessed at.
    """
    offered = [p.strip() for p in scope.get('subprotocols') or []]
    if len(offered) == 2 and offered[0] == TOKEN_SUBPROTOCOL:
        return offered[1]
    return None


def extract_token(scope):
    """Return ``(raw_token, source)`` for a handshake, or ``(None, None)``."""
    token = _subprotocol_token(scope)
    if token:
        return token, 'subprotocol'

    from django.conf import settings

    cookie_name = getattr(settings, 'ACCESS_COOKIE_NAME', None)
    if cookie_name:
        token = _cookies(scope).get(cookie_name)
        if token:
            return token, 'cookie'

    query = parse_qs((scope.get('query_string') or b'').decode('utf-8'))
    values = query.get('token') or []
    if values and values[0]:
        return values[0], 'query'

    return None, None


@database_sync_to_async
def _authenticate(raw_token, scope):
    """Validate the token and return the user, or None if it must be rejected.

    Wrapped in ``database_sync_to_async`` because both the user lookup and the
    hijack check touch the ORM, and a handshake runs on the event loop.
    """
    # Imported lazily: this module is imported from asgi.py, which must not touch
    # the app registry before get_asgi_application() has populated it.
    from rest_framework_simplejwt.authentication import JWTAuthentication

    from apps.security.authentication import enforce_token_security

    backend = JWTAuthentication()
    try:
        validated_token = backend.get_validated_token(raw_token)
        user = backend.get_user(validated_token)
    except (AuthenticationFailed, TokenError) as exc:
        logger.info('WebSocket handshake rejected: invalid token (%s)', exc.__class__.__name__)
        return None

    try:
        enforce_token_security(user, validated_token, _ScopeRequest(scope))
    except AuthenticationFailed as exc:
        logger.warning(
            'WebSocket handshake rejected for user %s: %s',
            getattr(user, 'id', None),
            getattr(exc, 'detail', exc),
        )
        return None

    return user


class JWTAuthMiddleware:
    """Populate ``scope['user']`` from a bearer token on the handshake.

    Three outcomes, and the distinction between the last two matters:

    * No token — leave whatever the session stack resolved. A browser logged into
      Django admin keeps working.
    * Valid token — override ``scope['user']``. This runs *below* the session
      stack (see ``JWTAuthMiddlewareStack``) precisely so it gets the last word.
    * Token present but rejected — force ``AnonymousUser``. Falling back to the
      session user here would mean a denylisted token silently downgrades to
      whatever cookie happens to be attached, which is how a force-logout gets
      undone.

    Rejecting the handshake outright is left to the consumer: it owns the close
    code the client sees, and ``connect()`` is where a 4001 can be sent
    intelligibly.
    """

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        raw_token, source = extract_token(scope)

        # A client that offered Sec-WebSocket-Protocol requires the server to echo
        # one of the offered values back, or it fails the handshake itself. The
        # consumers read this when calling accept(), so record what may be echoed
        # here rather than making every consumer re-parse the subprotocol list.
        extra = {}
        if source == 'subprotocol':
            extra['ws_subprotocol'] = TOKEN_SUBPROTOCOL

        if raw_token:
            if source == 'query':
                logger.warning(
                    'WebSocket token supplied in the query string (path=%s). '
                    'Prefer the %s subprotocol: query strings are written to '
                    'access logs.',
                    scope.get('path'),
                    TOKEN_SUBPROTOCOL,
                )
            user = await _authenticate(raw_token, scope)
            extra['user'] = user or AnonymousUser()
            extra['token_source'] = source

        if extra:
            scope = dict(scope, **extra)

        return await self.inner(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    """Session stack on the outside, JWT on the inside.

    Order is deliberate. Channels' ``AuthMiddleware.resolve_scope`` assigns
    ``scope['user']`` unconditionally, so a JWT middleware wrapped *around* the
    session stack would have its result overwritten by the session lookup —
    silently, and only for clients that happen to carry a session cookie. Running
    JWT underneath means it sees the session-resolved user and replaces it.

    The session stack is kept because it also provides ``scope['session']``, which
    ``AuthMiddleware`` requires and other code may read.
    """
    return AuthMiddlewareStack(JWTAuthMiddleware(inner))
