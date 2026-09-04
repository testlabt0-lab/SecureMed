"""
Views for accounts app: authentication, biometric, user management.
"""
import base64 
import io 
import secrets 

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
)
from apps .audit .utils import log_security_event 
from apps .audit .device_tracker import DeviceTracker 
from apps .security .session_security import SessionManager 
from apps .security .throttling import BiometricRateThrottle ,LoginRateThrottle 
from apps .security .crypto import encrypt_field ,decrypt_field 
from apps .security .models import LoginHistory, BlockedDevice
import hashlib 

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')

def get_tokens_for_user (user ,request =None ):
    """Generate JWT tokens for user."""
    refresh =RefreshToken .for_user (user )

    if request :
        ip =request .META .get ('REMOTE_ADDR','')
        ua =request .META .get ('HTTP_USER_AGENT','')
        fingerprint =hashlib .sha256 (f"{ip }:{ua }".encode ('utf-8')).hexdigest ()
        refresh ['client_fingerprint']=fingerprint 

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
                    
                    BlockedDevice.objects.get_or_create(
                        device_fingerprint=fingerprint,
                        defaults={
                            'reason': f'Blocked at level {new_level} ({attempts} attempts)',
                            'mac_address': mac_address,
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

        # Comment_26
        device_info ={
        'ip_address': ip_address,
        'mac_address': mac_address,
        'device_fingerprint': fingerprint,
        'os_info': os_info,
        'browser_info': browser_info
        }
        tracked =DeviceTracker .track_device (user ,request ,device_info )
        device ,is_new_device =tracked if tracked else (None ,False )

        # Comment_27
        needs_mfa =False 
        mfa_method ='none'

        if user .mfa_enabled and user .mfa_secret :
            needs_mfa =True 
            mfa_method ='totp'
        elif getattr (settings ,'ADAPTIVE_MFA_ENABLED',False )and (is_new_device or (device and not device .is_trusted )):
        # Comment_28
            needs_mfa =True 
            mfa_method ='email'

        if needs_mfa :
            mfa_token =secrets .token_urlsafe (32 )
            cache .set (f'mfa_pending:{mfa_token }',str (user .id ),timeout =300 )# Comment_29

            if mfa_method =='email':
                import random 
                otp_code =f"{random .randint (100000 ,999999 )}"
                cache .set (f'mfa_code:{mfa_token }',otp_code ,timeout =300 )

                # Comment_30
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

            # Comment_31
        user .last_login =timezone .now ()
        user .last_login_ip = ip_address
        user .save (update_fields =['last_login','last_login_ip'])

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
        event_type ='LOGIN_SUCCESS',
        request =request ,
        details ={'method':'password'}
        )

        return Response ({
        'tokens':tokens ,
        'user':UserSerializer (user ).data ,
        'requires_biometric':user .is_biometric_enabled ,
        })


class LogoutView (APIView ):
    """Logout by blacklisting the refresh token."""

    def post (self ,request ):
        try :
            refresh_token =request .data .get ('refresh')
            if refresh_token :
                token =RefreshToken (refresh_token )
                token .blacklist ()

            if request .user .is_authenticated :
                SessionManager .force_logout_user (request .user .id )

            log_security_event (
            user =request .user ,
            event_type ='LOGOUT',
            request =request ,
            )
            return Response ({'detail':'تم تسجيل الخروج بنجاح'})
        except TokenError :
            return Response (
            {'detail':'الرمز غير صالح'},
            status =status .HTTP_400_BAD_REQUEST 
            )


class RefreshTokenView (APIView ):
    """Refresh access token."""
    permission_classes =[permissions .AllowAny ]

    def post (self ,request ):
        refresh_token =request .data .get ('refresh')
        if not refresh_token :
            return Response (
            {'detail':'رمز التحديث مطلوب'},
            status =status .HTTP_400_BAD_REQUEST 
            )
        try :
            token =RefreshToken (refresh_token )
            return Response ({
            'access':str (token .access_token ),
            })
        except TokenError :
            return Response (
            {'detail':'رمز التحديث غير صالح أو منتهي'},
            status =status .HTTP_401_UNAUTHORIZED 
            )


class BiometricEnrollView (APIView ):
    """
    Enroll biometric authentication for the current user.
    Security requirement #4: تسجيل الدخول بالبصمة
    """

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
                    
                    BlockedDevice.objects.get_or_create(
                        device_fingerprint=fingerprint,
                        defaults={
                            'reason': f'Blocked at level {new_level} ({attempts} attempts) via biometric',
                            'mac_address': mac_address,
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

        # Comment_32
        device_info ={
        'ip_address':ip_address,
        'mac_address':mac_address,
        'device_fingerprint':fingerprint,
        'os_info':os_info,
        'browser_info':browser_info,
        }
        DeviceTracker .track_device (user ,request ,device_info )
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

        return Response ({
        'tokens':tokens ,
        'user':UserSerializer (user ).data ,
        })


class UserViewSet (viewsets .ModelViewSet ):
    """User management (admin only)."""
    queryset =User .objects .all ().order_by ('-created_at')
    serializer_class =UserSerializer 
    permission_classes =[IsAdminOrSelf ]
    filterset_fields =['role','is_active','department','basin']
    search_fields =['email','full_name','license_number']
    ordering_fields =['created_at','email','full_name']

    def get_permissions (self ):
        if self .action in ['create','destroy','update','partial_update']:
            return [permissions .IsAuthenticated (),IsAdminOrSelf ()]
        return [permissions .IsAuthenticated ()]

    def get_queryset (self ):
        qs =super ().get_queryset ()
        # Comment_33
        # Comment_34
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


        # Comment_35
        # Comment_36
        # Comment_37

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

            # Comment_38
        cached_code =cache .get (f'mfa_code:{mfa_token }')
        is_valid =False 

        if cached_code :
        # Comment_39
            is_valid =(code ==cached_code )
        else :
        # Comment_40
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

            # Comment_41
        trust_device =request .data .get ('trust_device',False )
        if trust_device :
            fingerprint =request .META .get ('HTTP_X_DEVICE_FINGERPRINT')
            if fingerprint :
                from apps .security .models import DeviceRegistry 
                DeviceRegistry .objects .filter (
                user =user ,device_fingerprint =fingerprint 
                ).update (is_trusted =True )

        cache .delete (f'mfa_pending:{mfa_token }')
        if cached_code :
            cache .delete (f'mfa_code:{mfa_token }')

        user .last_login =timezone .now ()
        user .last_login_ip =request .META .get ('REMOTE_ADDR')
        user .save (update_fields =['last_login','last_login_ip'])
        tokens =get_tokens_for_user (user ,request )
        log_security_event (
        user =user ,event_type ='MFA_LOGIN_SUCCESS',request =request ,
        )
        return Response ({
        'tokens':tokens ,
        'user':UserSerializer (user ).data ,
        })


        # Comment_42
        # Comment_43
        # Comment_44

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


        # Comment_45
        # Comment_46
        # Comment_47

class GlobalSearchView (APIView ):
    """Cross-entity search (Ctrl+K). Results are permission-scoped."""

    def get (self ,request ):
        q =(request .query_params .get ('q')or '').strip ()
        if len (q )<2 :
            return Response ({'patients':[],'channels':[],'users':[],'total':0 })

        from apps .channels .models import Channel 
        from apps .patients .models import Patient 

        user =request .user 
        is_admin =user .role in ['SUPER_ADMIN','HOSPITAL_ADMIN']

        # Comment_48
        patients =[]
        for p in Patient .objects .all ()[:500 ]:
            name =p .full_name or ''
            nid =p .national_id or ''
            if q .lower ()in name .lower ()or (nid and q in nid ):
                patients .append ({
                'id':str (p .id ),
                'full_name':name ,
                'national_id':nid ,
                'gender':p .gender ,
                'blood_type':p .blood_type ,
                })
            if len (patients )>=6 :
                break 

                # Comment_49
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

        # Comment_50
        users =[]
        if user .role not in ['AUDITOR']:
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


        # Comment_51
        # Comment_52
        # Comment_53
        # Comment_54
        # Comment_55
        # Comment_56
        # Comment_57
        # Comment_58
        # Comment_59
        # Comment_60
        # Comment_61
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

            # Comment_62
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

        # Comment_63
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
