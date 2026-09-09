"""
Views for accounts app: authentication, biometric, user management.
"""
import base64
import hmac
import io
import secrets
from datetime import timedelta

import pyotp 
import qrcode 
from rest_framework import status ,viewsets ,permissions ,serializers as drf_serializers 
from rest_framework .decorators import action 
from rest_framework .response import Response 
from rest_framework .views import APIView 
from rest_framework_simplejwt .tokens import RefreshToken 
from rest_framework_simplejwt .exceptions import TokenError 
from django .conf import settings 
from django .utils import timezone 
from django .db import transaction 
from django .core .cache import cache 
from django .db .models import Q 

from apps .accounts .models import User ,BiometricProfile 
from apps .accounts .serializers import (
UserSerializer ,UserCreateSerializer ,LoginSerializer ,
BiometricEnrollSerializer ,BiometricChallengeSerializer ,
BiometricLoginSerializer ,ChangePasswordSerializer ,
build_registration_options ,
)
from apps .audit .utils import log_security_event 
from apps .audit .device_tracker import DeviceTracker 
from apps .security .session_security import SessionManager 
from apps .security .throttling import BiometricRateThrottle ,LoginRateThrottle 
from apps .security .crypto import encrypt_field ,decrypt_field 
from apps .security .models import LoginHistory, BlockedDevice
from apps .security .authentication import BoundJWTAuthentication
from apps .core .net import client_fingerprint ,get_client_ip as _canonical_client_ip
import hashlib

def get_client_ip(request):
    """Deprecated shim — kept so existing call sites keep working."""
    return _canonical_client_ip(request)

REFRESH_COOKIE_NAME ='refresh_token'


def set_refresh_cookie (response ,refresh_token ):
    """Attach the refresh token as an HttpOnly cookie.

    One helper so the flags cannot drift between the password, MFA, biometric and
    refresh responses. max_age tracks REFRESH_TOKEN_LIFETIME — the cookie used to
    be pinned at seven days while the token inside it expired after one, which
    only teaches the browser to keep replaying a dead credential.
    """
    lifetime =settings .SIMPLE_JWT .get ('REFRESH_TOKEN_LIFETIME')
    max_age =int (lifetime .total_seconds ())if lifetime else 86400
    response .set_cookie (
    REFRESH_COOKIE_NAME ,
    refresh_token ,
    httponly =True ,
    secure =not settings .DEBUG ,
    samesite ='Strict',
    max_age =max_age ,
    path ='/',
    )
    return response

def get_tokens_for_user (user ,request =None ):
    """Generate JWT tokens for user."""
    refresh =RefreshToken .for_user (user )

    if request :
        refresh ['client_fingerprint']=client_fingerprint (request )

    # Session id claim. simplejwt copies custom claims from the refresh token onto
    # the access tokens minted from it, so both sides of a session share one `sid`
    # — which is what makes it possible to end *one* session on logout instead of
    # every session the user has (see SessionManager.end_session).
    refresh ['sid']=str (refresh ['jti'])

    return {
    'refresh':str (refresh ),
    'access':str (refresh .access_token ),
    'jti':str (refresh ['jti']),
    }


class IsAdminOrSelf (permissions .BasePermission ):
    """Allow admins full access, users can only access their own data."""

    def has_permission (self ,request ,view ):
        return request .user and request .user .is_authenticated 

    def has_object_permission (self ,request ,view ,obj ):
        if request .user .role in ['SUPER_ADMIN','HOSPITAL_ADMIN']:
            return True 
        return obj ==request .user 

class IsAdmin (permissions .BasePermission ):
    """Allow only admins."""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role in ['SUPER_ADMIN', 'HOSPITAL_ADMIN']


class LoginView (APIView ):
    """Email + password login. Returns a 2FA challenge when TOTP is enabled."""
    permission_classes =[permissions .AllowAny ]
    throttle_classes =[LoginRateThrottle ]

    def post (self ,request ):
        ip_address = get_client_ip(request)
        fingerprint = request.META.get('HTTP_X_DEVICE_FINGERPRINT', '')
        mac_address = request.META.get('HTTP_X_MAC_ADDRESS', '')
        os_info = request.META.get('HTTP_X_OS_INFO', '')
        browser_info = request.META.get('HTTP_X_BROWSER_INFO', '')
        
        # Check if currently blocked
        if fingerprint:
            block_key = f"blocked_device_{fingerprint}"
            if cache.get(block_key):
                raise drf_serializers.ValidationError({'error': 'تم حظر هذا الجهاز. يرجى المحاولة بعد انتهاء مدة الحظر.'})

        serializer =LoginSerializer (data =request .data )
        try :
            serializer .is_valid (raise_exception =True )
        except drf_serializers .ValidationError as e :
            # Log failed login attempt
            email = request.data.get('email', '')
            user = User.objects.filter(email=email).first() if email else None
            
            if fingerprint:
                cache_key = f"failed_login_device_{fingerprint}"
                level_key = f"failed_login_level_{fingerprint}"
                
                attempts = cache.get(cache_key, 0) + 1
                cache.set(cache_key, attempts, timeout=86400)
                
                if attempts >= 5:
                    level = cache.get(level_key, 0)
                    if level == 0:
                        timeout_seconds = 30 * 60
                        new_level = 1
                    elif level == 1:
                        timeout_seconds = 5 * 3600
                        new_level = 2
                    else:
                        timeout_seconds = 12 * 3600
                        new_level = 3
                        
                    cache.set(block_key, True, timeout=timeout_seconds)
                    cache.set(level_key, new_level, timeout=timeout_seconds + 86400)
                    cache.delete(cache_key) # Reset attempts for next block cycle

                    # update_or_create, not get_or_create: the row is what
                    # WAFMiddleware enforces, and with get_or_create a device
                    # blocked once kept its first reason forever and — since the
                    # model had no expiry — stayed blocked for good. Mirror the
                    # escalating cache lockout so the block lifts by itself.
                    BlockedDevice.objects.update_or_create(
                        device_fingerprint=fingerprint,
                        defaults={
                            'reason': f'Blocked at level {new_level} ({attempts} attempts)',
                            'mac_address': mac_address,
                            'is_active': True,
                            'expires_at': timezone.now() + timedelta(seconds=timeout_seconds),
                        }
                    )
            
            if user:
                LoginHistory.objects.create(
                    user=user,
                    ip_address=ip_address,
                    device_fingerprint=fingerprint,
                    os_info=os_info,
                    browser_info=browser_info,
                    is_success=False,
                    failure_reason=str(e.detail)
                )

            log_security_event(
                user=user,
                event_type='LOGIN_FAILED',
                request=request,
                severity='WARNING',
                details={'reason': str(e.detail), 'email_attempted': email}
            )
            raise e

        user =serializer .validated_data ['user']
        
        # Clear failure counts on success
        if fingerprint:
            cache.delete(f"failed_login_device_{fingerprint}")
            cache.delete(f"failed_login_level_{fingerprint}")

        # Device Tracking (early evaluation for Adaptive Auth)
        device_info ={
        'ip_address': ip_address,
        'mac_address': mac_address,
        'device_fingerprint': fingerprint,
        'os_info': os_info,
        'browser_info': browser_info
        }
        tracked =DeviceTracker .track_device (user ,request ,device_info )
        device ,is_new_device =tracked if tracked else (None ,False )

        # Enforce Dr. Majed's requirement: No login from unauthorized devices.
        # The setting exists so a deployment can opt out for testing without
        # deleting the code path; the default is True (deny).
        if getattr(settings, 'ENFORCE_DEVICE_AUTHORIZATION', True) and device and not device.is_trusted:
            log_security_event(
                user=user,
                event_type='LOGIN_FAILED',
                request=request,
                details={'reason': 'untrusted_device', 'device_fingerprint': fingerprint},
                severity='WARNING'
            )
            return Response(
                {'detail': 'الجهاز غير مصرح بالدخول. يرجى التواصل مع الإدارة للتفعيل.', 'authorized': False},
                status=status.HTTP_403_FORBIDDEN
        )

        # Determine if we need MFA (TOTP enabled)
        needs_mfa =False 
        mfa_method ='none'

        if user .mfa_enabled and user .mfa_secret :
            needs_mfa =True 
            mfa_method ='totp'

        if needs_mfa :
            mfa_token =secrets .token_urlsafe (32 )
            cache .set (f'mfa_pending:{mfa_token }',str (user .id ),timeout =300 )# 5 min

            if mfa_method =='email':
                # secrets, not random: randint is predictable when the process
                # state is known, and an OTP that can be predicted is a second
                # password printed into an email.
                otp_code =f"{secrets .randbelow (900000 )+100000 :06d}"
                cache .set (f'mfa_code:{mfa_token }',otp_code ,timeout =300 )

                # Send OTP via email
                from utils .email_service import send_securemed_email 
                send_securemed_email (
                to_email =user .email ,
                subject ='رمز التحقق بخطوتين — SecureMed',
                title ='محاولة دخول من جهاز جديد',
                body_html =f"<p>لقد رصدنا محاولة تسجيل دخول من جهاز جديد أو غير موثوق. رمز التحقق الخاص بك هو: <b>{otp_code }</b></p>",
                footer_note ='صالح لمدة 5 دقائق'
                )

            log_security_event (
            user =user ,
            event_type ='LOGIN_CHALLENGE',
            request =request ,
            details ={'method':mfa_method ,'mfa_pending':True ,'is_new_device':is_new_device },
            )
            return Response ({
            'requires_2fa':True ,
            'mfa_token':mfa_token ,
            'method':mfa_method ,
            'detail':'يجب إدخال رمز التحقق بخطوتين',
            })

            # Update login metadata
        user.last_login = timezone.now()
        # get_client_ip, not REMOTE_ADDR directly: behind the production proxy
        # REMOTE_ADDR is the proxy's own address, so every login was recorded from
        # the same IP and last_login_ip was useless for spotting a stolen account.
        user.last_login_ip = get_client_ip(request)
        user.save(update_fields=['last_login', 'last_login_ip'])
        
        # Log successful login history
        fingerprint = request.META.get('HTTP_X_DEVICE_FINGERPRINT', '')
        LoginHistory.objects.create(
            user=user,
            ip_address=user.last_login_ip,
            device_fingerprint=fingerprint,
            os_info=request.META.get('HTTP_X_OS_INFO', ''),
            browser_info=request.META.get('HTTP_X_BROWSER_INFO', ''),
            is_success=True
        )
        tokens =get_tokens_for_user (user ,request )
        SessionManager .register_session (user ,request ,token =tokens )
        
        log_security_event (
        user =user ,
        event_type ='LOGIN_SUCCESS',
        request =request ,
        details ={'method':'password'}
        )

        response = Response ({
        'tokens':tokens ,
        'user':UserSerializer (user ).data ,
        'requires_biometric':user .is_biometric_enabled ,
        })
        set_refresh_cookie (response ,tokens ['refresh'])
        return response


class LogoutView (APIView ):
    """Logout by blacklisting the refresh token and ending this one session.

    It used to call force_logout_user, which denies every token the account
    holds: signing out on a phone also signed the user out of the workstation
    they were working on. Only the session presenting the token is ended here —
    force_logout_user stays for the admin action and for hijack detection.
    """

    def post (self ,request ):
        try :
            refresh_token =request .COOKIES .get (REFRESH_COOKIE_NAME )or request .data .get ('refresh')
            session_id =None
            if refresh_token :
                token =RefreshToken (refresh_token )
                # `sid` is stable across rotation; jti is the pre-rotation value
                # register_session recorded. Try both so either shape matches.
                session_id =token .get ('sid')or str (token .get ('jti')or '')
                token .blacklist ()

            if request .user .is_authenticated :
                if session_id :
                    SessionManager .end_session (request .user .id ,session_id )
                else :
                    # No token to identify the session — the safe reading of
                    # "log me out" is then to end all of them.
                    SessionManager .force_logout_user (request .user .id )

            log_security_event (
            user =request .user ,
            event_type ='LOGOUT',
            request =request ,
            )
            response = Response ({'detail':'تم تسجيل الخروج بنجاح'})
            response .delete_cookie (REFRESH_COOKIE_NAME )
            return response
        except TokenError :
            return Response (
            {'detail':'الرمز غير صالح'},
            status =status .HTTP_400_BAD_REQUEST
            )


class RefreshTokenView (APIView ):
    """Exchange a refresh token for a new access token, rotating the refresh token.

    SIMPLE_JWT already declares ROTATE_REFRESH_TOKENS and BLACKLIST_AFTER_ROTATION,
    but those are honoured by simplejwt's own TokenRefreshView — this custom view
    bypassed them, so a single refresh token stayed valid for its entire lifetime
    and a stolen one could be replayed until it expired. Rotation, denylist and
    device-binding checks are therefore done explicitly here.
    """
    permission_classes =[permissions .AllowAny ]

    def post (self ,request ):
        refresh_token =request .COOKIES .get (REFRESH_COOKIE_NAME )or request .data .get ('refresh')
        if not refresh_token :
            return Response (
            {'detail':'رمز التحديث مطلوب'},
            status =status .HTTP_400_BAD_REQUEST
            )
        try :
            token =RefreshToken (refresh_token )
        except TokenError :
            return Response (
            {'detail':'رمز التحديث غير صالح أو منتهي'},
            status =status .HTTP_401_UNAUTHORIZED
            )

        user =User .objects .filter (pk =token .get ('user_id')).first ()

        # The same binding BoundJWTAuthentication enforces on every API call. The
        # claim is deliberately NOT re-derived from this request: rebinding here
        # would let whoever holds a stolen refresh token re-point the session at
        # their own IP and user agent, which is the exact attack the binding exists
        # to stop.
        bound =token .get ('client_fingerprint')
        if bound and bound !=client_fingerprint (request ):
            log_security_event (
            user =user ,
            event_type ='SESSION_HIJACK_DETECTED',
            request =request ,
            severity ='CRITICAL',
            details ={'reason':'refresh_fingerprint_mismatch'},
            )
            return self ._reject ('الجلسة غير مطابقة لهذا الجهاز. يرجى تسجيل الدخول مرة أخرى.')

        # A force-logout denies every token issued before it. Without this the
        # refresh endpoint keeps minting access tokens for a session that an
        # administrator — or the user — has already terminated.
        denied_since =cache .get (f'token_denylist:{token .get ("user_id")}')
        if denied_since and BoundJWTAuthentication ._issued_before (token ,denied_since ):
            return self ._reject ('الجلسة غير صالحة. يرجى تسجيل الدخول مرة أخرى.')

        if user is None or not user .is_active :
            return self ._reject ('الحساب غير مفعّل')

        rotated =None
        if settings .SIMPLE_JWT .get ('ROTATE_REFRESH_TOKENS'):
            if settings .SIMPLE_JWT .get ('BLACKLIST_AFTER_ROTATION'):
                try :
                    token .blacklist ()
                except AttributeError :
                    pass # Comment: token_blacklist app not installed
            token .set_jti ()
            token .set_exp ()
            token .set_iat ()
            rotated =str (token )

        payload ={'access':str (token .access_token )}
        if rotated :
            payload ['refresh']=rotated

        response =Response (payload )
        if rotated :
            set_refresh_cookie (response ,rotated )
        return response

    def _reject (self ,detail ):
        """401 and clear the cookie, so a browser stops replaying a dead token."""
        response =Response ({'detail':detail },status =status .HTTP_401_UNAUTHORIZED )
        response .delete_cookie (REFRESH_COOKIE_NAME )
        return response


class BiometricEnrollView (APIView ):
    """Enroll a device's public-key credential for the signed-in user.

    Security requirement #4: تسجيل الدخول بالبصمة

    GET returns the creation options — including the challenge, which the server
    now issues and remembers. The web client used to generate its own challenge,
    so the whole registration could be assembled without the server ever being
    involved in the ceremony.
    """

    def get (self ,request ):
        return Response (build_registration_options (request .user ))

    def post (self ,request ):
        serializer =BiometricEnrollSerializer (
        data =request .data ,context ={'request':request }
        )
        serializer .is_valid (raise_exception =True )
        profile =serializer .save ()

        log_security_event (
        user =request .user ,
        event_type ='BIOMETRIC_ENROLLMENT',
        request =request ,
        details ={'device_id':profile .device_id ,'platform':profile .platform }
        )
        return Response ({
        'detail':'تم تسجيل البصمة بنجاح',
        'device_id':profile .device_id ,
        },status =status .HTTP_201_CREATED )


class BiometricChallengeView (APIView ):
    """Request a challenge for biometric login."""
    permission_classes =[permissions .AllowAny ]
    throttle_classes =[BiometricRateThrottle ]

    def post (self ,request ):
        serializer =BiometricChallengeSerializer (data =request .data )
        serializer .is_valid (raise_exception =True )
        result =serializer .save ()

        log_security_event (
        user =serializer .validated_data ['user'],
        event_type ='BIOMETRIC_CHALLENGE_REQUESTED',
        request =request ,
        )
        return Response (result )


class BiometricLoginView (APIView ):
    """
    Verify biometric login.
    Security requirement #4: الاعتماد على البصمة في عمليات التحقق
    """
    permission_classes =[permissions .AllowAny ]
    throttle_classes =[BiometricRateThrottle ]

    def post (self ,request ):
        ip_address = get_client_ip(request)
        fingerprint = request.META.get('HTTP_X_DEVICE_FINGERPRINT', '')
        mac_address = request.META.get('HTTP_X_MAC_ADDRESS', '')
        os_info = request.META.get('HTTP_X_OS_INFO', '')
        browser_info = request.META.get('HTTP_X_BROWSER_INFO', '')

        if fingerprint:
            block_key = f"blocked_device_{fingerprint}"
            if cache.get(block_key):
                raise drf_serializers.ValidationError({'error': 'تم حظر هذا الجهاز. يرجى المحاولة بعد انتهاء مدة الحظر.'})

        serializer =BiometricLoginSerializer (data =request .data )
        try:
            serializer .is_valid (raise_exception =True )
        except drf_serializers.ValidationError as e:
            # Handle failed biometric login
            if fingerprint:
                cache_key = f"failed_login_device_{fingerprint}"
                level_key = f"failed_login_level_{fingerprint}"
                
                attempts = cache.get(cache_key, 0) + 1
                cache.set(cache_key, attempts, timeout=86400)
                
                if attempts >= 5:
                    level = cache.get(level_key, 0)
                    if level == 0:
                        timeout_seconds = 30 * 60
                        new_level = 1
                    elif level == 1:
                        timeout_seconds = 5 * 3600
                        new_level = 2
                    else:
                        timeout_seconds = 12 * 3600
                        new_level = 3
                        
                    cache.set(block_key, True, timeout=timeout_seconds)
                    cache.set(level_key, new_level, timeout=timeout_seconds + 86400)
                    cache.delete(cache_key)

                    # See the password-login path: update_or_create + expires_at,
                    # so the WAF-enforced row expires with the cache lockout.
                    BlockedDevice.objects.update_or_create(
                        device_fingerprint=fingerprint,
                        defaults={
                            'reason': f'Blocked at level {new_level} ({attempts} attempts) via biometric',
                            'mac_address': mac_address,
                            'is_active': True,
                            'expires_at': timezone.now() + timedelta(seconds=timeout_seconds),
                        }
                    )
            
            # Note: We can't easily know the user here because the challenge ID might be invalid.
            # But log_security_event will still log it anonymously.
            log_security_event(
                user=None,
                event_type='LOGIN_FAILED',
                request=request,
                severity='WARNING',
                details={'reason': str(e.detail), 'method': 'biometric'}
            )
            raise e
            
        user =serializer .validated_data ['user']

        if fingerprint:
            cache.delete(f"failed_login_device_{fingerprint}")
            cache.delete(f"failed_login_level_{fingerprint}")

        user .last_login =timezone .now ()
        user .last_login_ip =ip_address
        user .save (update_fields =['last_login','last_login_ip'])

        # Device Tracking
        device_info ={
        'ip_address':ip_address,
        'mac_address':mac_address,
        'device_fingerprint':fingerprint,
        'os_info':os_info,
        'browser_info':browser_info,
        }
        tracked = DeviceTracker.track_device(user, request, device_info)
        device, _ = tracked if tracked else (None, False)

        # Enforce Dr. Majed's requirement: No login from unauthorized devices
        if getattr(settings, 'ENFORCE_DEVICE_AUTHORIZATION', True) and device and not device.is_trusted:
            log_security_event(
                user=user,
                event_type='LOGIN_FAILED',
                request=request,
                details={'reason': 'untrusted_device_biometric', 'device_fingerprint': fingerprint},
                severity='WARNING'
            )
            return Response(
                {'detail': 'الجهاز غير مصرح بالدخول. يرجى التواصل مع الإدارة للتفعيل.', 'authorized': False},
                status=status.HTTP_403_FORBIDDEN
            )

        tokens =get_tokens_for_user (user ,request )
        SessionManager .register_session (user ,request ,token =tokens )
        
        LoginHistory.objects.create(
            user=user,
            ip_address=ip_address,
            device_fingerprint=fingerprint,
            os_info=os_info,
            browser_info=browser_info,
            is_success=True,
        )
        
        log_security_event (
        user =user ,
        event_type ='BIOMETRIC_LOGIN_SUCCESS',
        request =request ,
        )

        response = Response ({
        'tokens':tokens ,
        'user':UserSerializer (user ).data ,
        })
        set_refresh_cookie (response ,tokens ['refresh'])
        return response


class UserViewSet (viewsets .ModelViewSet ):
    """User management (admin only)."""
    queryset =User .objects .all ().order_by ('-created_at')
    serializer_class =UserSerializer 
    permission_classes =[IsAdminOrSelf ]
    filterset_fields =['role','is_active','department','basin']
    search_fields =['email','full_name','license_number']
    ordering_fields =['created_at','email','full_name']

    def get_permissions (self ):
        if self .action =='create':
            return [permissions .IsAuthenticated (),IsAdmin ()]
        if self .action in ['destroy','update','partial_update']:
            return [permissions .IsAuthenticated (),IsAdminOrSelf ()]
        return [permissions .IsAuthenticated ()]

    def get_queryset (self ):
        qs =super ().get_queryset ()
        # Basin scoping: a basin-bound HOSPITAL_ADMIN manages only their
        # basin's users (plan requirement: linkage by basin).
        from apps .basins .utils import basin_scoped_queryset 
        return basin_scoped_queryset (qs ,self .request .user ,lookup ='basin_id')

    def get_serializer_class (self ):
        if self .action =='create':
            return UserCreateSerializer 
        return UserSerializer 

    @action (detail =False ,methods =['get','put','patch'])
    def me (self ,request ):
        """Get or update current user."""
        if request .method =='GET':
            return Response (UserSerializer (request .user ).data )
        serializer =UserSerializer (
        request .user ,data =request .data ,partial =True 
        )
        serializer .is_valid (raise_exception =True )
        serializer .save ()
        return Response (serializer .data )

    @action (detail =False ,methods =['post'])
    def change_password (self ,request ):
        serializer =ChangePasswordSerializer (
        data =request .data ,context ={'request':request }
        )
        serializer .is_valid (raise_exception =True )
        serializer .save ()
        log_security_event (
        user =request .user ,
        event_type ='PASSWORD_CHANGED',
        request =request ,
        )
        return Response ({'detail':'تم تغيير كلمة المرور بنجاح'})

    @action (detail =True ,methods =['post'])
    def deactivate (self ,request ,pk =None ):
        """Deactivate a user (admin only)."""
        if request .user .role not in ['SUPER_ADMIN','HOSPITAL_ADMIN']:
            return Response (
            {'detail':'غير مصرح'},
            status =status .HTTP_403_FORBIDDEN 
            )
        user =self .get_object ()
        user .is_active =False 
        user .save ()
        log_security_event (
        user =request .user ,
        event_type ='USER_DEACTIVATED',
        request =request ,
        details ={'target_user':str (user .id )}
        )
        return Response ({'detail':'تم إلغاء تفعيل المستخدم'})

    @action (detail =True ,methods =['post'])
    def activate (self ,request ,pk =None ):
        """Re-activate a deactivated user (admin only)."""
        if request .user .role not in ['SUPER_ADMIN','HOSPITAL_ADMIN']:
            return Response (
            {'detail':'غير مصرح'},
            status =status .HTTP_403_FORBIDDEN 
            )
        user =self .get_object ()
        user .is_active =True 
        user .failed_login_attempts =0 
        user .locked_until =None 
        user .save (update_fields =[
        'is_active','failed_login_attempts','locked_until'
        ])
        log_security_event (
        user =request .user ,
        event_type ='USER_ACTIVATED',
        request =request ,
        details ={'target_user':str (user .id )}
        )
        return Response ({'detail':'تم تفعيل المستخدم'})

    @action (detail =False ,methods =['get'])
    def by_role (self ,request ):
        """Get users filtered by role."""
        role =request .query_params .get ('role')
        if not role :
            return Response (
            {'detail':'البارامتر role مطلوب'},
            status =status .HTTP_400_BAD_REQUEST 
            )
        users =User .objects .filter (role =role ,is_active =True )
        return Response (UserSerializer (users ,many =True ).data )


        # ============================================================
        # Two-Factor Authentication (TOTP) — DevSecOps security layer
        # ============================================================

def _qr_data_uri (text :str )->str :
    """Render otpauth:// URI as a base64 PNG data URI."""
    img =qrcode .make (text )
    buf =io .BytesIO ()
    img .save (buf ,format ='PNG')
    return 'data:image/png;base64,'+base64 .b64encode (buf .getvalue ()).decode ()


class MFAStatusView (APIView ):
    """Whether the current user has 2FA enabled."""

    def get (self ,request ):
        return Response ({
        'mfa_enabled':bool (request .user .mfa_enabled ),
        'mfa_created_at':request .user .mfa_created_at ,
        })


class MFASetupView (APIView ):
    """Generate a TOTP secret + QR code for the current user (not yet enabled)."""

    def post (self ,request ):
        if request .user .mfa_enabled :
            return Response (
            {'detail':'التحقق بخطوتين مفعل بالفعل'},
            status =status .HTTP_400_BAD_REQUEST ,
            )
        secret =pyotp .random_base32 ()
        encrypted =encrypt_field (secret )
        request .user .mfa_secret =encrypted 
        request .user .save (update_fields =['mfa_secret'])

        totp =pyotp .TOTP (secret )
        uri =totp .provisioning_uri (
        name =request .user .email ,issuer_name ='SecureMed'
        )
        return Response ({
        'secret':secret ,
        'otpauth_url':uri ,
        'qr_image':_qr_data_uri (uri ),
        'detail':'امسح رمز QR بتطبيق المصادقة ثم أكّد الرمز',
        })


class MFAVerifyView (APIView ):
    """Verify a TOTP code and enable 2FA for the current user."""

    def post (self ,request ):
        code =(request .data .get ('code')or '').strip ()
        if not code or not request .user .mfa_secret :
            return Response (
            {'detail':'ابدأ الإعداد أولاً ثم أدخل الرمز'},
            status =status .HTTP_400_BAD_REQUEST ,
            )
        try :
            secret =decrypt_field (request .user .mfa_secret )
        except Exception :
            return Response (
            {'detail':'سر التحقق غير صالح، أعد الإعداد'},
            status =status .HTTP_400_BAD_REQUEST ,
            )
        totp =pyotp .TOTP (secret )
        if not totp .verify (code ,valid_window =1 ):
            log_security_event (
            user =request .user ,event_type ='MFA_LOGIN_FAILED',
            request =request ,details ={'stage':'verify_enable'},
            severity ='WARNING',
            )
            return Response (
            {'detail':'رمز التحقق غير صحيح'},
            status =status .HTTP_400_BAD_REQUEST ,
            )
        request .user .mfa_enabled =True 
        request .user .mfa_created_at =timezone .now ()
        request .user .save (update_fields =['mfa_enabled','mfa_created_at'])
        log_security_event (
        user =request .user ,event_type ='MFA_ENABLED',request =request ,
        )
        return Response ({'detail':'تم تفعيل التحقق بخطوتين بنجاح'})


class MFADisableView (APIView ):
    """Disable 2FA after verifying a valid TOTP code."""

    def post (self ,request ):
        code =(request .data .get ('code')or '').strip ()
        if not request .user .mfa_enabled :
            return Response (
            {'detail':'التحقق بخطوتين غير مفعل'},
            status =status .HTTP_400_BAD_REQUEST ,
            )
        secret =decrypt_field (request .user .mfa_secret )
        if not pyotp .TOTP (secret ).verify (code ,valid_window =1 ):
            log_security_event (
            user =request .user ,event_type ='MFA_LOGIN_FAILED',
            request =request ,details ={'stage':'disable'},
            severity ='WARNING',
            )
            return Response (
            {'detail':'رمز التحقق غير صحيح'},
            status =status .HTTP_400_BAD_REQUEST ,
            )
        request .user .mfa_enabled =False 
        request .user .mfa_secret =''
        request .user .mfa_created_at =None 
        request .user .save (update_fields =['mfa_enabled','mfa_secret','mfa_created_at'])
        log_security_event (
        user =request .user ,event_type ='MFA_DISABLED',request =request ,
        severity ='WARNING',
        )
        return Response ({'detail':'تم تعطيل التحقق بخطوتين'})


class MFALoginView (APIView ):
    """Complete login with the pending 2FA token + TOTP code."""
    permission_classes =[permissions .AllowAny ]
    throttle_classes =[BiometricRateThrottle ]

    def post (self ,request ):
        mfa_token =request .data .get ('mfa_token')or ''
        code =(request .data .get ('code')or '').strip ()
        user_id =cache .get (f'mfa_pending:{mfa_token }')
        if not user_id :
            return Response (
            {'detail':'انتهت صلاحية الجلسة، سجل الدخول من جديد'},
            status =status .HTTP_401_UNAUTHORIZED ,
            )
        try :
            user =User .objects .get (id =user_id )
        except User .DoesNotExist :
            return Response (
            {'detail':'المستخدم غير موجود'},
            status =status .HTTP_401_UNAUTHORIZED ,
            )

            # Check if it's an email OTP
        cached_code =cache .get (f'mfa_code:{mfa_token }')
        is_valid =False 

        if cached_code :
        # Verify Email OTP. compare_digest, not ==: equality on short strings
        # short-circuits byte by byte and is observable through timing.
            is_valid =hmac .compare_digest (code ,cached_code )
        else :
        # Verify TOTP
            if not user .mfa_secret :
                return Response ({'detail':'إعدادات التحقق غير صالحة'},status =400 )
            secret =decrypt_field (user .mfa_secret )
            is_valid =pyotp .TOTP (secret ).verify (code ,valid_window =1 )

        if not is_valid :
            log_security_event (
            user =user ,event_type ='MFA_LOGIN_FAILED',request =request ,
            severity ='WARNING',
            )
            return Response (
            {'detail':'رمز التحقق غير صحيح'},
            status =status .HTTP_400_BAD_REQUEST ,
            )

        # Device authorization gate — LoginView and BiometricLoginView both
        # enforce it, but this view was a gap: a caller on an untrusted device
        # could complete 2FA and receive tokens anyway. Same rule, same place
        # in the flow: checked after the secret verifies, before anything is
        # minted.
        fingerprint =request .META .get ('HTTP_X_DEVICE_FINGERPRINT','')
        if fingerprint :
            from apps .security .models import BlockedDevice ,DeviceRegistry 
            from apps .audit .device_tracker import DeviceTracker 
            if DeviceTracker .is_device_blocked (fingerprint )or (
            BlockedDevice .objects .enforceable ()
            .filter (device_fingerprint =fingerprint ).exists ()
            ):
                log_security_event (
                user =user ,event_type ='LOGIN_FAILED',request =request ,
                details ={'reason':'blocked_device_mfa',
                          'device_fingerprint':fingerprint},
                severity ='WARNING',
                )
                return Response (
                {'detail':'هذا الجهاز محظور.','authorized':False },
                status =status .HTTP_403_FORBIDDEN ,
                )
            if getattr (settings ,'ENFORCE_DEVICE_AUTHORIZATION',True ):
                device =DeviceRegistry .objects .filter (
                user =user ,device_fingerprint =fingerprint 
                ).first ()
                if device is None or not device .is_trusted :
                    log_security_event (
                    user =user ,event_type ='LOGIN_FAILED',request =request ,
                    details ={'reason':'untrusted_device_mfa',
                              'device_fingerprint':fingerprint},
                    severity ='WARNING',
                    )
                    return Response (
                    {'detail':'الجهاز غير مصرح بالدخول. يرجى التواصل مع الإدارة للتفعيل.',
                     'authorized':False },
                    status =status .HTTP_403_FORBIDDEN ,
                    )

        # Trust this device if requested. Self-trust is the historical
        # adaptive-auth behaviour, and it is a hole in Dr. Majed's activation
        # policy: with ENFORCE_DEVICE_AUTHORIZATION on, activation must come
        # from the admin (Telegram/dashboard) only — a client asking for trust
        # here would mint its own license, even for a blacklisted device.
        trust_device =request .data .get ('trust_device',False )
        if trust_device and not getattr (settings ,'ENFORCE_DEVICE_AUTHORIZATION',True ):
            fingerprint =request .META .get ('HTTP_X_DEVICE_FINGERPRINT')
            if fingerprint :
                from apps .security .models import DeviceRegistry ,BlockedDevice 
                if not BlockedDevice .objects .enforceable ().filter (
                device_fingerprint =fingerprint 
                ).exists ():
                    DeviceRegistry .objects .filter (
                    user =user ,device_fingerprint =fingerprint 
                    ).update (is_trusted =True )

        cache .delete (f'mfa_pending:{mfa_token }')
        if cached_code :
            cache .delete (f'mfa_code:{mfa_token }')

        user .last_login =timezone .now ()
        user .last_login_ip =get_client_ip (request )
        user .save (update_fields =['last_login','last_login_ip'])
        tokens =get_tokens_for_user (user ,request )
        # Register the session exactly as LoginView and BiometricLoginView do.
        # Without this, a 2FA login minted tokens for a session that was never
        # recorded in `active_sessions`, with two consequences: the concurrent
        # session limit did not apply to it, and — for any client that sends
        # X-Device-Fingerprint — SessionManager.is_session_valid found the
        # request's fingerprint in no live session and reject_if_hijacked
        # force-logged-out the whole account on the first authenticated call.
        SessionManager .register_session (user ,request ,token =tokens )
        
        # Log successful login history
        fingerprint = request.META.get('HTTP_X_DEVICE_FINGERPRINT', '')
        LoginHistory.objects.create(
            user=user,
            ip_address=user.last_login_ip,
            device_fingerprint=fingerprint,
            os_info=request.META.get('HTTP_X_OS_INFO', ''),
            browser_info=request.META.get('HTTP_X_BROWSER_INFO', ''),
            is_success=True
        )

        log_security_event (
        user =user ,event_type ='MFA_LOGIN_SUCCESS',request =request ,
        )
        response = Response ({
        'tokens':tokens ,
        'user':UserSerializer (user ).data ,
        })
        set_refresh_cookie (response ,tokens ['refresh'])
        return response


        # ============================================================
        # Biometric device management (list / revoke / delete)
        # ============================================================

class BiometricDeviceSerializer (drf_serializers .ModelSerializer ):
    class Meta :
        model =BiometricProfile 
        fields =[
        'id','device_id','device_name','platform',
        'is_active','last_used','created_at',
        ]


class IsProfileOwnerOrAdmin (permissions .BasePermission ):
    """Object permission for biometric device profiles."""

    def has_object_permission (self ,request ,view ,obj ):
        if request .user .role in ['SUPER_ADMIN','HOSPITAL_ADMIN']:
            return True 
        return obj .user_id ==request .user .id 


class BiometricProfileViewSet (viewsets .ReadOnlyModelViewSet ):
    """List/revoke biometric devices (admin or self)."""
    serializer_class =BiometricDeviceSerializer 
    permission_classes =[permissions .IsAuthenticated ,IsProfileOwnerOrAdmin ]

    def get_queryset (self ):
        user =self .request .user 
        if user .role in ['SUPER_ADMIN','HOSPITAL_ADMIN']:
            return BiometricProfile .objects .all ().order_by ('-created_at')
        return BiometricProfile .objects .filter (user =user ).order_by ('-created_at')

    @action (detail =True ,methods =['post'])
    def revoke (self ,request ,pk =None ):
        """Revoke (deactivate) a biometric device."""
        profile =self .get_object ()
        profile .is_active =False 
        profile .save (update_fields =['is_active','updated_at'])
        log_security_event (
        user =request .user ,
        event_type ='BIOMETRIC_REVOKED',
        request =request ,
        details ={'profile_id':str (profile .id )}
        )
        return Response ({'detail':'تم إلغاء الجهاز البيوميتري'})

    @action (detail =True ,methods =['delete'])
    def remove (self ,request ,pk =None ):
        """Delete a biometric device entirely."""
        profile =self .get_object ()
        device_id =profile .device_id 
        profile .delete ()
        log_security_event (
        user =request .user ,
        event_type ='BIOMETRIC_REVOKED',
        request =request ,
        details ={'profile_id':str (pk ),'device_id':device_id ,'deleted':True }
        )
        return Response ({'detail':'تم حذف الجهاز البيوميتري'})


        # ============================================================
        # Global search — patients / channels / users in one query
        # ============================================================

class GlobalSearchView (APIView ):
    """Cross-entity search (Ctrl+K). Results are permission-scoped."""

    # Patient name / national id are Fernet-encrypted properties over TextField
    # columns, so they CANNOT be matched with SQL icontains — the scan below is
    # unavoidable. What matters is that it iterates an already-scoped queryset,
    # never Patient.objects.all(). This cap bounds the decrypt cost per request.
    PATIENT_SCAN_LIMIT = 500

    def get (self ,request ):
        q =(request .query_params .get ('q')or '').strip ()
        if len (q )<2 :
            return Response ({'patients':[],'channels':[],'users':[],'total':0 })

        from apps .channels .models import Channel
        from apps .patients .models import Patient
        from apps .core .mixins import (
        NON_CLINICAL_ROLES ,
        PATIENT_INDEX_ADMIN_ROLES ,
        accessible_patients ,
        )

        user =request .user
        is_admin =user .role in PATIENT_INDEX_ADMIN_ROLES

        # Scope BEFORE scanning: accessible_patients() applies basin scoping and
        # then the channel-membership rule. This previously read
        # Patient.objects.all(), so any authenticated account — including the
        # PATIENT role, which is the default for new users — could enumerate
        # every patient's name and national id.
        patients =[]
        needle =q .lower ()
        patient_qs =accessible_patients (
        Patient .objects .all (),user
        ).only (
        '_full_name','_national_id','gender','blood_type'
        )[:self .PATIENT_SCAN_LIMIT ]
        for p in patient_qs :
            name =p .full_name or ''
            nid =p .national_id or ''
            if needle in name .lower ()or (nid and q in nid ):
                patients .append ({
                'id':str (p .id ),
                'full_name':name ,
                'national_id':nid ,
                'gender':p .gender ,
                'blood_type':p .blood_type ,
                })
            if len (patients )>=6 :
                break

                # --- Channels (visibility-scoped) ---
        if is_admin :
            channels_qs =Channel .objects .all ()
        else :
            channels_qs =Channel .objects .filter (
            Q (owner =user )|Q (memberships__user =user ,memberships__is_active =True )
            ).distinct ()
        channels =[
        {
        'id':str (c .id ),
        'name':c .name ,
        'channel_type':c .channel_type ,
        'priority':c .priority ,
        'status':c .status ,
        }
        for c in channels_qs .filter (
        Q (name__icontains =q )|Q (description__icontains =q )
        ).order_by ('-created_at')[:6 ]
        ]

        # Staff directory: withheld from AUDITOR (separation of duties) and from
        # non-clinical roles, which previously could enumerate every account's
        # name, email and role.
        users =[]
        if user .role not in ('AUDITOR',)+NON_CLINICAL_ROLES :
            for u in User .objects .filter (
            Q (full_name__icontains =q )|Q (email__icontains =q )
            ).order_by ('full_name')[:6 ]:
                users .append ({
                'id':str (u .id ),
                'full_name':u .full_name ,
                'email':u .email ,
                'role':u .role ,
                'role_display':u .get_role_display (),
                })

        return Response ({
        'patients':patients ,
        'channels':channels ,
        'users':users ,
        'total':len (patients )+len (channels )+len (users ),
        })


        # ---------------------------------------------------------------------------
        # Password reset (forgot password) — anonymous, rate-limited, audited.
        #
        # Flow (three steps, no user enumeration at any point):
        #   1) POST /auth/password/reset/          {email}       → always the same reply
        #   2) Email with a one-time signed link  (valid 1 hour)
        #   3) POST /auth/password/reset/confirm/ {uid, token,
        #                                          new_password} → password changed
        # The token uses Django's PasswordResetTokenGenerator: bound to the user's
        # password hash + last_login, so it self-invalidates after use or change.
        # ---------------------------------------------------------------------------
from django .contrib .auth .tokens import default_token_generator 
from django .utils .encoding import force_bytes ,force_str 
from django .utils .http import urlsafe_base64_encode ,urlsafe_base64_decode 

from apps .accounts .serializers import (
PasswordResetRequestSerializer ,
PasswordResetConfirmSerializer ,
)
from apps .security .throttling import PasswordResetRateThrottle 


class PasswordResetRequestView (APIView ):
    """POST /auth/password/reset/ — email a one-time reset link (anonymous)."""
    permission_classes =[permissions .AllowAny ]
    throttle_classes =[PasswordResetRateThrottle ]

    def post (self ,request ):
        serializer =PasswordResetRequestSerializer (data =request .data )
        serializer .is_valid (raise_exception =True )
        email =serializer .validated_data ['email'].lower ().strip ()

        user =User .objects .filter (email =email ,is_active =True ).first ()
        if user is not None :
            uid =urlsafe_base64_encode (force_bytes (user .pk ))
            token =default_token_generator .make_token (user )
            reset_link =f"{settings .FRONTEND_URL }/forgot-password?uid={uid }&token={token }"

            from utils .email_service import send_securemed_email 
            sent =send_securemed_email (
            to_email =email ,
            subject ='استعادة كلمة المرور — SecureMed',
            title ='استعادة كلمة المرور',
            body_html =f"""
                    <p>تحية طيبة،</p>
                    <p>توصلنا بطلب لإعادة تعيين كلمة المرور الخاصة بحسابكم في منصة
                    <b>SecureMed</b>. إذا كنتم صاحب الطلب، اضغطوا الزر أدناه لاختيار
                    كلمة مرور جديدة:</p>
                    <p style="text-align:center;margin:22px 0;">
                      <a href="{reset_link }"
                         style="background:#2563EB;color:#ffffff;text-decoration:none;
                                padding:12px 28px;border-radius:8px;font-weight:bold;
                                display:inline-block;">إعادة تعيين كلمة المرور</a>
                    </p>
                    <p style="color:#6B7280;font-size:13px;">
                      أو انسخوا الرابط التالي إلى المتصفح:<br>
                      <span style="word-break:break-all;color:#2563EB;">{reset_link }</span>
                    </p>
                    <p style="color:#6B7280;font-size:13px;">
                      ⏱ الرابط صالح لمدة ساعة واحدة فقط ويمكن استخدامه مرة واحدة.<br>
                      🔒 إذا لم تكونوا طلبتم الاستعادة، تجاهلوا هذه الرسالة —
                      كلمة مروركم الحالية ستبقى كما هي.
                    </p>
                """,
            footer_note ='رسالة تلقائية — لا تردوا عليها',
            )

            log_security_event (
            user =user ,
            event_type ='PASSWORD_RESET_REQUESTED',
            request =request ,
            details ={'email':email ,'email_sent':bool (sent )},
            )

            # Identical response whether or not the account exists (no enumeration)
        return Response ({
        'detail':'إذا كان هذا البريد مسجلاً لدينا، ستصل رسالة تحتوي رابط '
        'إعادة التعيين خلال دقائق. تفضلوا بفحص صندوق الوارد '
        'ومجلد الرسائل غير المرغوبة.',
        })


class PasswordResetConfirmView (APIView ):
    """POST /auth/password/reset/confirm/ — set a new password (anonymous)."""
    permission_classes =[permissions .AllowAny ]
    throttle_classes =[PasswordResetRateThrottle ]

    def post (self ,request ):
        serializer =PasswordResetConfirmSerializer (data =request .data )
        serializer .is_valid (raise_exception =True )
        data =serializer .validated_data 

        # Resolve the user from the base64 uid
        try :
            uid =force_str (urlsafe_base64_decode (data ['uid']))
            user =User .objects .filter (pk =uid ,is_active =True ).first ()
        except (ValueError ,TypeError ,OverflowError ):
            user =None 

        if user is None or not default_token_generator .check_token (user ,data ['token']):
            return Response (
            {'detail':'الرابط غير صالح أو منتهي الصلاحية. '
            'يرجى طلب رابط جديد.'},
            status =status .HTTP_400_BAD_REQUEST ,
            )

        user .set_password (data ['new_password'])
        user .save (update_fields =['password'])

        log_security_event (
        user =user ,
        event_type ='PASSWORD_RESET_COMPLETED',
        request =request ,
        details ={'method':'email_reset_link'},
        )

        return Response ({
        'detail':'تم تحديث كلمة المرور بنجاح. يمكنك الآن تسجيل الدخول '
        'بكلمة المرور الجديدة.',
        })

from django.contrib.auth.models import Permission

class GrantPermissionView(APIView):
    """Grant a specific permission to a user (Super Admin only)."""
    permission_classes = [permissions.IsAuthenticated, IsAdminOrSelf]

    def post(self, request, pk=None):
        if request.user.role not in ['SUPER_ADMIN', 'HOSPITAL_ADMIN']:
            return Response({'detail': 'غير مصرح'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'detail': 'المستخدم غير موجود'}, status=status.HTTP_404_NOT_FOUND)

        permission_codename = request.data.get('permission')
        if not permission_codename:
            return Response({'detail': 'يجب تحديد الصلاحية'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            perm = Permission.objects.get(codename=permission_codename)
            user.user_permissions.add(perm)
            log_security_event(
                user=request.user,
                event_type='PERMISSION_GRANTED',
                request=request,
                details={'target_user': str(user.id), 'permission': permission_codename}
            )
            return Response({'detail': f'تم منح صلاحية {permission_codename} بنجاح'})
        except Permission.DoesNotExist:
            return Response({'detail': 'الصلاحية غير موجودة'}, status=status.HTTP_400_BAD_REQUEST)

class RevokePermissionView(APIView):
    """Revoke a specific permission from a user (Super Admin only)."""
    permission_classes = [permissions.IsAuthenticated, IsAdminOrSelf]

    def post(self, request, pk=None):
        if request.user.role not in ['SUPER_ADMIN', 'HOSPITAL_ADMIN']:
            return Response({'detail': 'غير مصرح'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'detail': 'المستخدم غير موجود'}, status=status.HTTP_404_NOT_FOUND)

        permission_codename = request.data.get('permission')
        if not permission_codename:
            return Response({'detail': 'يجب تحديد الصلاحية'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            perm = Permission.objects.get(codename=permission_codename)
            user.user_permissions.remove(perm)
            log_security_event(
                user=request.user,
                event_type='PERMISSION_REVOKED',
                request=request,
                details={'target_user': str(user.id), 'permission': permission_codename}
            )
            return Response({'detail': f'تم سحب صلاحية {permission_codename} بنجاح'})
        except Permission.DoesNotExist:
            return Response({'detail': 'الصلاحية غير موجودة'}, status=status.HTTP_400_BAD_REQUEST)
