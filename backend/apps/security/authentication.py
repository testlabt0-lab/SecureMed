from django .core .cache import cache
from rest_framework_simplejwt .authentication import JWTAuthentication
from rest_framework_simplejwt .exceptions import AuthenticationFailed

from apps .core .net import client_fingerprint


def enforce_token_security(user, validated_token, request):
    """Run every post-signature check an access token must survive.

    Verifying the JWT signature only proves the token was minted by us; it says
    nothing about whether the session behind it is still allowed to exist. These
    four checks are what actually revoke access, and they have to run on *every*
    authenticated entry point or the weakest one becomes the way in.

    Lives at module level rather than inside BoundJWTAuthentication because
    WebSocket handshakes need the identical checks and do not go through DRF
    (see ``apps.security.channels_auth``). Two copies of this logic would drift,
    and the copy that drifted would be the one holding the door open.

    ``request`` only has to expose ``META`` — a real HttpRequest, a DRF Request,
    or the scope shim the Channels middleware builds all satisfy that.

    Raises AuthenticationFailed if the token must be rejected.
    """
    # Account-wide force-logout: denies every token issued before the marker.
    denied_since = cache.get(f'token_denylist:{user.id}')
    if denied_since and _issued_before(validated_token, denied_since):
        raise AuthenticationFailed(
            'الجلسة غير صالحة. يرجى تسجيل الدخول مرة أخرى.', code='session_invalidated'
        )

    # Per-session denylist — set when *this* session logged out, so signing out
    # on one device does not have to invalidate the user's other sessions.
    from apps.security.session_security import SessionManager

    if SessionManager.is_session_denied(validated_token.get('sid')):
        raise AuthenticationFailed(
            'الجلسة منتهية. يرجى تسجيل الدخول مرة أخرى.', code='session_ended'
        )

    # Token binding: the claim is derived by apps.core.net at issue time, so
    # issuing and verifying cannot diverge.
    token_fingerprint = validated_token.get('client_fingerprint')
    if token_fingerprint and token_fingerprint != client_fingerprint(request):
        raise AuthenticationFailed(
            'Token binding mismatch. IP or User-Agent changed.', code='token_hijacked'
        )

    # Device-fingerprint check. SessionSecurityMiddleware cannot do this for API
    # traffic — request.user is still anonymous when middleware runs, because DRF
    # authenticates inside the view — so it is enforced here, where the user is
    # known, against the same SessionManager rule.
    #
    # `sid` scopes the comparison to the session this token belongs to. Left
    # unscoped, the rule compared against every session the user has, so the
    # concurrent-session limit evicting one client's record turned that client's
    # next request into a force-logout of the whole account.
    if SessionManager.reject_if_hijacked(
        user, request, session_id=validated_token.get('sid')
    ):
        raise AuthenticationFailed(
            'تم رصد نشاط مريب. يرجى تسجيل الدخول مرة أخرى.', code='session_invalidated'
        )


def _issued_before(validated_token, denied_since):
    """True when this token predates the force-logout marker.

    The marker used to be a bare flag, which rejected *every* token for its whole
    TTL — including the ones minted by the login that followed, so a user who
    logged out could not log back in. Comparing issue times revokes only what
    existed before the logout.
    """
    if denied_since is True:  # legacy marker written before this fix
        return True
    issued_at = validated_token.get('iat')
    if issued_at is None:
        return True
    try:
        return float(issued_at) < float(denied_since)
    except (TypeError, ValueError):
        return True


class BoundJWTAuthentication (JWTAuthentication ):
    """
    Custom JWT Authentication that validates the client_fingerprint claim.
    The claim must match a hash of the current IP address and User-Agent.
    """
    def get_validated_token (self ,raw_token ):
        validated_token =super ().get_validated_token (raw_token )
        return validated_token

    def authenticate (self ,request ):
        auth_result =super ().authenticate (request )
        if auth_result is None :
            return None

        user ,validated_token =auth_result
        enforce_token_security (user ,validated_token ,request )
        return user ,validated_token

    @staticmethod
    def _issued_before (validated_token ,denied_since ):
        """Retained for callers outside this module; see module-level _issued_before."""
        return _issued_before (validated_token ,denied_since )
