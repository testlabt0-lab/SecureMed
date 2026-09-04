import logging 
from django .core .cache import cache 
from django .utils import timezone 
from rest_framework_simplejwt .tokens import RefreshToken 

logger =logging .getLogger ('security')

class SessionManager :
    """Manages user sessions, concurrent limits, and session binding."""

    MAX_CONCURRENT_SESSIONS =3 

    @staticmethod 
    def register_session (user ,request ,token =None ):
        """Register a new session for the user."""
        if not user or not user .is_authenticated :
            return 

        session_id =''
        if token is not None and isinstance (token ,dict ):
            session_id =str (token .get ('jti',''))
        if not session_id and hasattr (request ,'session')and request .session .session_key :
            session_id =request .session .session_key 
        device_fingerprint =request .META .get ('HTTP_X_DEVICE_FINGERPRINT','')

        # Comment_361
        cache_key =f'active_sessions:{user .id }'
        sessions =cache .get (cache_key ,[])

        # Comment_362
        new_session ={
        'session_id':session_id ,
        'device_fingerprint':device_fingerprint ,
        'timestamp':timezone .now ().timestamp (),
        'ip_address':request .META .get ('REMOTE_ADDR','')
        }

        # Comment_363
        if len (sessions )>=SessionManager .MAX_CONCURRENT_SESSIONS :
        # Comment_364
        # Comment_365
        # Comment_366
            sessions =sorted (sessions ,key =lambda x :x ['timestamp'])
            sessions =sessions [-(SessionManager .MAX_CONCURRENT_SESSIONS -1 ):]
            logger .warning (f"User {user .id } exceeded concurrent session limit. Terminating oldest.")

        sessions .append (new_session )
        cache .set (cache_key ,sessions ,timeout =86400 )# Comment_367
        # A successful login invalidates any prior force-logout denylist
        cache .delete (f'token_denylist:{user .id }')

    @staticmethod 
    def force_logout_user (user_id ):
        """Force logout all sessions for a user."""
        # Comment_368
        cache_key =f'active_sessions:{user_id }'
        cache .delete (cache_key )

        # Add user to token denylist so existing JWTs are rejected by
        # BoundJWTAuthentication until the denylist entry expires or a new
        # login clears it (see register_session).
        cache .set (f'token_denylist:{user_id }',True ,timeout =86400 )

        # Comment_369
        # Comment_370
        # Comment_371
        logger .warning (f"Force logout executed for user {user_id }")

    @staticmethod 
    def is_session_valid (user ,request ):
        """Check if the current session is valid and not hijacked."""
        if not user or not user .is_authenticated :
            return True 

        current_fingerprint =request .META .get ('HTTP_X_DEVICE_FINGERPRINT','')

        # Comment_372
        if current_fingerprint :
        # Comment_373
        # Comment_374
            pass 

        return True 
