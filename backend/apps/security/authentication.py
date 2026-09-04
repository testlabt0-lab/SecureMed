import hashlib 
from django .core .cache import cache 
from rest_framework_simplejwt .authentication import JWTAuthentication 
from rest_framework_simplejwt .exceptions import AuthenticationFailed 

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

        # Check token denylist — rejects JWTs issued before a force-logout
        if cache .get (f'token_denylist:{user .id }'):
            raise AuthenticationFailed ('الجلسة غير صالحة. يرجى تسجيل الدخول مرة أخرى.',code ='session_invalidated')

        # Comment_309
        token_fingerprint =validated_token .get ('client_fingerprint')
        if token_fingerprint :
            ip =request .META .get ('REMOTE_ADDR','')
            ua =request .META .get ('HTTP_USER_AGENT','')
            current_fingerprint =hashlib .sha256 (f"{ip }:{ua }".encode ('utf-8')).hexdigest ()

            if token_fingerprint !=current_fingerprint :
                raise AuthenticationFailed ('Token binding mismatch. IP or User-Agent changed.',code ='token_hijacked')

        return user ,validated_token 
