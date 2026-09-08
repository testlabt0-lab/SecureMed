import logging
from django .core .cache import cache
from django .utils import timezone
from rest_framework_simplejwt .tokens import RefreshToken

from apps .core .net import get_client_ip

logger =logging .getLogger ('security')

class SessionManager :
    """Manages user sessions, concurrent limits, and session binding."""

    MAX_CONCURRENT_SESSIONS = 1 

    @staticmethod 
    def register_session (user ,request ,token =None ):
        """Register a new session for the user and terminate old ones."""
        if not user or not user .is_authenticated :
            return 
            
        session_id =''
        if token is not None and isinstance (token ,dict ):
            session_id =str (token .get ('jti',''))
        if not session_id and hasattr (request ,'session')and request .session .session_key :
            session_id =request .session .session_key 
        device_fingerprint =request .META .get ('HTTP_X_DEVICE_FINGERPRINT','')

        # Track active sessions in cache
        cache_key =f'active_sessions:{user .id }'
        sessions =cache .get (cache_key ,[])

        # Denylist existing sessions to enforce MAX_CONCURRENT_SESSIONS = 1
        for old_session in sessions:
            old_session_id = old_session.get('session_id')
            if old_session_id and old_session_id != session_id:
                cache.set(f'session_denylist:{old_session_id}', True, timeout=3600)
                logger.info(f"Invalidated old session {old_session_id} for user {user.id}")

        # Add new session
        new_session ={
        'session_id':session_id ,
        'device_fingerprint':device_fingerprint ,
        'timestamp':timezone .now ().timestamp (),
        'ip_address':get_client_ip (request )
        }

        sessions = [new_session]
        cache .set (cache_key ,sessions ,timeout =86400 )# 24h

    @staticmethod
    def force_logout_user (user_id ):
        """Force logout all sessions for a user."""
        # Clear active sessions from cache
        cache_key =f'active_sessions:{user_id }'
        cache .delete (cache_key )

        # Store *when* revocation happened rather than a bare flag, so
        # BoundJWTAuthentication can tell revoked tokens from ones minted later.
        cache .set (f'token_denylist:{user_id }',timezone .now ().timestamp (),timeout =86400 )

        # Note: In JWT, we can't easily invalidate tokens without a token blacklist.
        # Simple JWT has a token blacklist app which we could use if we had the specific tokens.
        # Alternatively, we could increment a user 'security_stamp' field to invalidate all tokens.
        logger .warning (f"Force logout executed for user {user_id }")

    @staticmethod
    def end_session (user_id ,session_id ):
        """End one session, leaving the user's other sessions alone.

        An ordinary logout used to call :meth:`force_logout_user`, which denies
        every token the user holds — signing out on a phone also signed them out
        of the workstation they were mid-consultation on. This drops just that
        session and denies the tokens carrying its ``sid`` claim; the refresh
        token is blacklisted separately by the caller.
        """
        if not session_id :
            return

        cache_key =f'active_sessions:{user_id }'
        sessions =cache .get (cache_key ,[])
        remaining =[s for s in sessions if s .get ('session_id')!=str (session_id )]
        if remaining :
            cache .set (cache_key ,remaining ,timeout =86400 )
        else :
            cache .delete (cache_key )

        # Access tokens are self-contained, so the only way to stop the ones
        # already issued for this session is to name them. They live 15 minutes
        # (SIMPLE_JWT.ACCESS_TOKEN_LIFETIME); an hour of margin covers clock skew
        # and a rotated refresh token that kept the same sid.
        cache .set (f'session_denylist:{session_id }',True ,timeout =3600 )
        logger .info (f"Session {session_id } ended for user {user_id }")

    @staticmethod
    def is_session_denied (session_id ):
        """True when this session was explicitly ended (logout)."""
        if not session_id :
            return False
        return bool (cache .get (f'session_denylist:{session_id }'))

    @staticmethod
    def is_session_valid (user ,request ,session_id =None ):
        """False when this request's fingerprint contradicts *its own* session.

        Used to be a stub that always returned ``True``, so the hijack detection
        it was supposed to back did nothing. It was then written to compare the
        request's fingerprint against **every** live session of the user, which
        made two ordinary events look like theft: the concurrent-session limit
        evicting this client's record (:meth:`register_session` keeps only the
        newest ``MAX_CONCURRENT_SESSIONS``), and a cache flush. Since
        :meth:`reject_if_hijacked` answers with :meth:`force_logout_user`, a
        phone whose record had been evicted by three later logins signed the
        account out *everywhere* on its very next request — and only clients
        that send the header could trigger it, which is why the mobile app was
        blocked from sending it at all.

        The comparison is therefore scoped to the session the caller's own token
        names (the ``sid`` claim, recorded as ``session_id`` at registration).
        That is also the only comparison that carries a meaning: a token
        presented from a device other than the one it was issued to.

        Four cases deliberately return ``True`` rather than "suspicious",
        because treating them as an attack force-logs-out legitimate users:

        * the caller sent no ``X-Device-Fingerprint`` — there is nothing to
          compare, and JWT binding (IP + User-Agent) already covers that request;
        * no live record matches this session — it was evicted by the session
          limit or lost with the cache, neither of which is evidence of theft;
        * this session was registered without a fingerprint, by a client that
          does not send the header;
        * no registered session carries a fingerprint at all (legacy shape).
        """
        if not user or not user .is_authenticated :
            return True

        current_fingerprint =request .META .get ('HTTP_X_DEVICE_FINGERPRINT','')
        if not current_fingerprint :
            return True

        sessions =cache .get (f'active_sessions:{user .id }',[])

        if session_id :
            recorded =next (
            (s for s in sessions if str (s .get ('session_id',''))==str (session_id )),
            None ,
            )
            if recorded is None :
                return True
            registered_fingerprint =recorded .get ('device_fingerprint')
            if not registered_fingerprint :
                return True
            return current_fingerprint ==registered_fingerprint

        # Nothing to scope by: a token minted before the `sid` claim existed, or
        # a caller that cannot name its session. The union stays as the fallback
        # — looser, and still carrying the eviction false positive — because
        # there is no way to tighten it without knowing which session is asking.
        known =[s .get ('device_fingerprint')for s in sessions if s .get ('device_fingerprint')]
        if not known :
            return True

        return current_fingerprint in known

    @staticmethod
    def reject_if_hijacked (user ,request ,session_id =None ):
        """Force-logout and report the fingerprint mismatch, if there is one.

        Returns ``True`` when the request was rejected. Shared by the middleware
        (session-authenticated requests) and ``BoundJWTAuthentication`` (API
        requests), so both enforce one rule. [session_id] names the caller's own
        session — the ``sid`` claim for a JWT, the session key for a Django
        session — and both callers pass it, because without it the check widens
        to every live session and an evicted record reads as an attack.
        """
        if SessionManager .is_session_valid (user ,request ,session_id =session_id ):
            return False

        logger .warning (
        f"SESSION_HIJACK_ATTEMPT | User={user .id } | "
        f"Actual={request .META .get ('HTTP_X_DEVICE_FINGERPRINT','')[:64 ]}"
        )
        SessionManager .force_logout_user (user .id )
        return True
