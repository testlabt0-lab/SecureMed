"""
Serializers for accounts app.
"""
import logging
import uuid
from rest_framework import serializers
from django .conf import settings
from django .contrib .auth import password_validation
from django .core .cache import cache
from django .core .exceptions import ValidationError
from django .db .models import F
from django .utils import timezone
from django .utils .translation import gettext_lazy as _

from apps .accounts .models import User ,BiometricProfile ,BiometricChallenge
from apps .security .crypto import (
WebAuthnError ,COSE_ES256 ,COSE_RS256 ,
b64url_decode ,b64url_encode ,generate_auth_challenge ,
load_public_key ,public_key_to_pem ,
verify_webauthn_registration ,verify_webauthn_assertion ,verify_native_assertion ,
)

logger =logging .getLogger ('security')


class UserSerializer (serializers .ModelSerializer ):
    """Serializer for User model."""
    basin_name =serializers .CharField (source ='basin.name',read_only =True ,default ='')
    permissions = serializers.SerializerMethodField()
    groups = serializers.SerializerMethodField()

    def get_permissions(self, obj):
        if not obj.is_active:
            return []
        return list(obj.get_all_permissions())

    def get_groups(self, obj):
        return list(obj.groups.values_list('name', flat=True))

    class Meta :
        model =User 
        fields =[
        'id','email','full_name','phone','role',
        'license_number','department','specialization',
        'basin','basin_name',
        'is_active',
        'is_biometric_enabled','mfa_enabled','created_at',
        'permissions', 'groups'
        ]
        read_only_fields =['id','created_at','mfa_enabled', 'permissions', 'groups', 'role', 'is_active', 'basin']


class UserCreateSerializer (serializers .ModelSerializer ):
    """Serializer for creating new users (admin only)."""
    password =serializers .CharField (write_only =True ,required =True )
    password_confirm =serializers .CharField (write_only =True ,required =True )

    class Meta :
        model =User 
        fields =[
        'email','full_name','phone','role',
        'license_number','department','specialization',
        'basin',
        'password','password_confirm',
        ]

    def validate_password (self ,value ):
        try :
            password_validation .validate_password (value )
        except ValidationError as e :
            raise serializers .ValidationError (list (e .messages ))
        return value 

    def validate (self ,attrs ):
        if attrs ['password']!=attrs ['password_confirm']:
            raise serializers .ValidationError (
            {'password_confirm':_ ('كلمتا المرور غير متطابقتين')}
            )
        return attrs 

    def create (self ,validated_data ):
        validated_data .pop ('password_confirm')
        password =validated_data .pop ('password')
        user =User .objects .create_user (password =password ,**validated_data )
        return user 


class LoginSerializer (serializers .Serializer ):
    """Serializer for email+password login."""
    email =serializers .EmailField ()
    password =serializers .CharField (write_only =True )

    def validate (self ,attrs ):
        email =attrs .get ('email')
        password =attrs .get ('password')

        if email and password :
            try :
                user =User .objects .get (email =email )
            except User .DoesNotExist :
                raise serializers .ValidationError (
                {'detail':'بيانات الاعتماد غير صحيحة'}
                )

            if user .is_locked :
            # Provide user-friendly localized time format or time remaining
                import humanize 
                import datetime 
                from django .utils import timezone 

                now =timezone .now ()
                if user .locked_until >now :
                    delta =user .locked_until -now 
                    minutes =int (delta .total_seconds ()/60 )
                    raise serializers .ValidationError (
                    {'detail':f'تم قفل الحساب مؤقتًا لدواع أمنية. يرجى المحاولة بعد {minutes } دقيقة.'}
                    )
                else :
                # Lock has expired, reset it
                    user .reset_failed_attempts ()

            if not user.check_password(password):
                user.failed_login_attempts += 1
                if user.failed_login_attempts >= 3:
                    user.lock_account()
                    from apps.notifications.utils import send_notification
                    admins = User.objects.filter(role__in=['SUPER_ADMIN', 'HOSPITAL_ADMIN'])
                    for admin in admins:
                        send_notification(
                            recipient=admin,
                            notification_type='SECURITY_ALERT',
                            title='محاولات دخول فاشلة متكررة',
                            message=f'تم قفل حساب المستخدم {user.email} بسبب تجاوز عدد محاولات الدخول الفاشلة.',
                            sender=None,
                            priority='HIGH'
                        )
                user.save()
                raise serializers .ValidationError (
                {'detail':'بيانات الاعتماد غير صحيحة'}
                )

            user .reset_failed_attempts ()
            attrs ['user']=user 
            return attrs 
        raise serializers .ValidationError (
        {'detail':'يجب إدخال البريد الإلكتروني وكلمة المرور'}
        )


def _registration_cache_key (user ):
    return f'webauthn:reg:{user .pk }'


def build_registration_options (user ):
    """Creation options for navigator.credentials.create(), challenge kept server-side.

    The browser used to invent this challenge itself — `webauthn.ts` said so in a
    comment — and a challenge the client chooses proves nothing, because the whole
    ceremony can then be assembled offline. Here the random bytes are cached under
    the user's id and the enrollment request is only accepted if the clientDataJSON
    it returns carries them back.
    """
    _raw ,challenge_b64 =generate_auth_challenge ()
    ttl =settings .BIOMETRIC_SETTINGS ['CHALLENGE_TTL_SECONDS']
    cache .set (_registration_cache_key (user ),challenge_b64 ,timeout =ttl )

    already_enrolled =list (
    BiometricProfile .objects .filter (user =user ,is_active =True )
    .exclude (credential_id ='')
    .values_list ('credential_id',flat =True )
    )
    return {
    'rp':{'id':settings .WEBAUTHN_RP_ID ,'name':settings .WEBAUTHN_RP_NAME },
    'user':{
    'id':b64url_encode (str (user .id ).encode ('utf-8')),
    'name':user .email ,
    'displayName':user .full_name or user .email ,
    },
    'challenge':challenge_b64 ,
    'pubKeyCredParams':[
    {'type':'public-key','alg':COSE_ES256 },
    {'type':'public-key','alg':COSE_RS256 },
    ],
    'timeout':ttl *1000 ,
    'attestation':'none',
    'authenticatorSelection':{
    'authenticatorAttachment':'platform',
    'residentKey':'preferred',
    'userVerification':'required',
    },
    'excludeCredentials':[
    {'type':'public-key','id':cid ,'transports':['internal']}
    for cid in already_enrolled
    ],
    }


class BiometricEnrollSerializer (serializers .Serializer ):
    """Enroll one device's public-key credential.

    Security requirement #4: تسجيل الدخول بالبصمة

    What arrives here is a *public* key, never a fingerprint. The previous version
    accepted `biometric_template`: an arbitrary client-chosen string that the server
    hashed and then compared on every later login, which made it a password the user
    can never change — and one that any client which had ever seen the string could
    present. The web client passed `JSON.stringify(credential)` as that string, so a
    later login would have had to reproduce a byte-identical WebAuthn credential
    object; since every ceremony carries a fresh signature, browser biometric login
    could not have succeeded even once.
    """
    device_id =serializers .CharField (max_length =255 )
    device_name =serializers .CharField (max_length =255 ,required =False ,allow_blank =True )
    platform =serializers .ChoiceField (choices =['ANDROID','IOS','WEB'])
    public_key =serializers .CharField (write_only =True )
    credential_id =serializers .CharField (required =False ,allow_blank =True )
    client_data_json =serializers .CharField (
    required =False ,allow_blank =True ,write_only =True )

    def validate (self ,attrs ):
        user =self .context ['request'].user

        if attrs ['platform']=='WEB':
            attrs ['public_key_pem']=self ._verify_web (user ,attrs )
        else :
        # Native platforms have no clientDataJSON to bind. The trust here comes
        # from the request being authenticated: the session already proves who is
        # enrolling, which is also why attestation is not parsed.
            try :
                attrs ['public_key_pem']=public_key_to_pem (
                load_public_key (attrs ['public_key']))
            except (WebAuthnError ,ValueError )as exc :
                logger .warning ('Biometric enrollment rejected for %s: %s',user .pk ,exc )
                raise serializers .ValidationError (
                {'detail':'المفتاح العام غير صالح'})
        return attrs

    def _verify_web (self ,user ,attrs ):
        """Check the WebAuthn create() response, return the key as SPKI PEM."""
        client_data =attrs .get ('client_data_json')or ''
        if not client_data or not (attrs .get ('credential_id')or ''):
            raise serializers .ValidationError (
            {'detail':'تسجيل WebAuthn يتطلب credential_id و client_data_json'})

        expected =cache .get (_registration_cache_key (user ))
        if not expected :
            raise serializers .ValidationError (
            {'detail':'انتهت صلاحية طلب التسجيل، أعد المحاولة'})

        try :
            key =verify_webauthn_registration (
            client_data_json =b64url_decode (client_data ),
            public_key_material =attrs ['public_key'],
            expected_challenge_b64 =expected ,
            allowed_origins =settings .WEBAUTHN_ALLOWED_ORIGINS ,
            )
        except (WebAuthnError ,ValueError )as exc :
        # The precise failure goes to the log only. Telling the caller that the
        # origin — rather than the challenge — was wrong hands a forger the next
        # thing to fix.
            logger .warning ('WebAuthn registration rejected for %s: %s',user .pk ,exc )
            raise serializers .ValidationError (
            {'detail':'فشل التحقق من بيانات الاعتماد البيومترية'})

        cache .delete (_registration_cache_key (user ))
        return public_key_to_pem (key )

    def create (self ,validated_data ):
        user =self .context ['request'].user
        profile ,_created =BiometricProfile .objects .update_or_create (
        user =user ,
        device_id =validated_data ['device_id'],
        defaults ={
        'device_name':validated_data .get ('device_name','')or '',
        'platform':validated_data ['platform'],
        'public_key':validated_data ['public_key_pem'],
        'credential_id':validated_data .get ('credential_id','')or '',
        'sign_count':0 ,
        'failed_attempts':0 ,
        'is_active':True ,
        # Deliberately blanked: the template hash and its salt belong to the old
        # shared-secret scheme, and private_key_encrypted must stay empty because a
        # server that holds the private key has thrown away the one property that
        # makes this stronger than a password.
        'biometric_hash':'',
        'salt':'',
        'private_key_encrypted':'',
        }
        )

        user .is_biometric_enabled =True
        user .biometric_enrolled_at =timezone .now ()
        user .save (update_fields =['is_biometric_enabled','biometric_enrolled_at'])
        logger .info ('Biometric credential enrolled: user=%s device=%s platform=%s',
        user .pk ,profile .device_id ,profile .platform )
        return profile


class BiometricChallengeSerializer (serializers .Serializer ):
    """Issue a single-use challenge for a biometric login.

    This endpoint is anonymous, so it answers identically whether or not the
    account exists. The previous version returned three distinguishable errors —
    «المستخدم غير موجود», «المصادقة البيومترية غير مفعلة», «الجهاز غير مسجل» —
    which made it an oracle for who holds an account, who has enrolled a device,
    and which device ids are registered. In a hospital system the first of those
    alone discloses that a named person is a patient here.
    """

    email =serializers .EmailField ()
    device_id =serializers .CharField (max_length =255 )

    def validate (self ,attrs ):
        profile =(
        BiometricProfile .objects
        .filter (
        user__email__iexact =attrs ['email'],
        device_id =attrs ['device_id'],
        is_active =True ,
        user__is_active =True ,
        user__is_biometric_enabled =True ,
        )
        .exclude (public_key ='')
        .select_related ('user')
        .first ()
        )
        # A locked account is treated exactly like a missing one: any difference
        # here would confirm the account exists.
        if profile is not None and profile .user .is_locked :
            logger .warning ('Biometric challenge refused, account locked: %s',
            profile .user .pk )
            profile =None

        attrs ['profile']=profile
        attrs ['user']=profile .user if profile is not None else None
        return attrs

    def create (self ,validated_data ):
        profile =validated_data ['profile']
        _raw ,challenge_b64 =generate_auth_challenge ()
        ttl =settings .BIOMETRIC_SETTINGS ['CHALLENGE_TTL_SECONDS']

        payload ={
        'challenge':challenge_b64 ,
        'rp_id':settings .WEBAUTHN_RP_ID ,
        'timeout':ttl *1000 ,
        'user_verification':(
        'required'if settings .WEBAUTHN_REQUIRE_USER_VERIFICATION else 'preferred'),
        'allow_credentials':[],
        }

        if profile is None :
        # Decoy. Shaped exactly like a real response but backed by no database
        # row, so it can never be answered: the login step looks the challenge id
        # up and finds nothing. The caller learns only that it got a challenge.
            payload ['challenge_id']=str (uuid .uuid4 ())
            return payload

        challenge =BiometricChallenge .objects .create (
        user =profile .user ,
        profile =profile ,
        challenge =challenge_b64 ,
        expires_at =timezone .now ()+timezone .timedelta (seconds =ttl ),
        )
        payload ['challenge_id']=str (challenge .id )
        if profile .credential_id :
        # allowCredentials tells the browser which enrolled key to use. Native
        # clients identify the credential by device_id and send nothing here.
            payload ['allow_credentials']=[{
            'type':'public-key',
            'id':profile .credential_id ,
            'transports':['internal'],
            }]
        return payload


class BiometricLoginSerializer (serializers .Serializer ):
    """Verify a signature over the challenge we issued; the view mints the tokens.

    Every rejection returns the same sentence. The reason is written to the security
    log instead, because «rpIdHash mismatch» or «counter did not advance» tells a
    forger exactly which part of the forgery to fix next.
    """
    challenge_id =serializers .UUIDField ()
    signature =serializers .CharField (write_only =True )
    # WebAuthn only. Native assertions sign the raw challenge bytes, so there is no
    # clientDataJSON and no authenticatorData to send.
    client_data_json =serializers .CharField (
    required =False ,allow_blank =True ,write_only =True )
    authenticator_data =serializers .CharField (
    required =False ,allow_blank =True ,write_only =True )

    GENERIC_ERROR ='فشل التحقق من المصادقة البيومترية'

    def _reject (self ,reason ,user =None ):
        logger .warning ('Biometric login rejected (user=%s): %s',
        getattr (user ,'pk',None ),reason )
        raise serializers .ValidationError ({'detail':self .GENERIC_ERROR })

    def validate (self ,attrs ):
        challenge =(
        BiometricChallenge .objects
        .select_related ('profile','profile__user','user')
        .filter (id =attrs ['challenge_id'])
        .first ()
        )
        if challenge is None :
        # Includes every decoy challenge handed out for an unknown account.
            self ._reject ('unknown challenge id')

        # Burn the nonce *before* verifying. A single UPDATE ... WHERE used = false
        # picks the winner inside the database, so two requests replaying the same
        # id concurrently cannot both proceed, and a wrong signature cannot be
        # retried against the same challenge. The old code read `is_valid` and only
        # called `mark_used()` after a successful verification, which left both
        # windows open.
        if not challenge .claim ():
            self ._reject ('challenge already used or expired',challenge .user )

        profile =challenge .profile
        if profile is None or not profile .is_active or not profile .public_key :
            self ._reject ('challenge has no active credential attached',challenge .user )

        user =profile .user
        if not user .is_active or user .is_locked :
            self ._reject ('account inactive or locked',user )

        try :
            sign_count =self ._verify (profile ,challenge ,attrs )
        except (WebAuthnError ,ValueError )as exc :
            self ._count_failure (profile ,user )
            self ._reject (str (exc ),user )

        profile .last_used =timezone .now ()
        profile .failed_attempts =0
        if sign_count >profile .sign_count :
            profile .sign_count =sign_count
        profile .save (update_fields =['last_used','failed_attempts','sign_count'])
        user .reset_failed_attempts ()

        attrs ['user']=user
        attrs ['profile']=profile
        return attrs

    def _verify (self ,profile ,challenge ,attrs ):
        """Return the authenticator's signature counter, or raise WebAuthnError."""
        public_key =load_public_key (profile .public_key )
        signature =b64url_decode (attrs ['signature'])

        if profile .platform =='WEB':
            if not (attrs .get ('client_data_json')and attrs .get ('authenticator_data')):
                raise WebAuthnError (
                'WEB credential requires clientDataJSON and authenticatorData')
            return verify_webauthn_assertion (
            public_key =public_key ,
            client_data_json =b64url_decode (attrs ['client_data_json']),
            authenticator_data =b64url_decode (attrs ['authenticator_data']),
            signature =signature ,
            expected_challenge_b64 =challenge .challenge ,
            rp_id =settings .WEBAUTHN_RP_ID ,
            allowed_origins =settings .WEBAUTHN_ALLOWED_ORIGINS ,
            require_user_verification =settings .WEBAUTHN_REQUIRE_USER_VERIFICATION ,
            stored_sign_count =profile .sign_count ,
            )

        return verify_native_assertion (
        public_key =public_key ,
        challenge =b64url_decode (challenge .challenge ),
        signature =signature ,
        )

    def _count_failure (self ,profile ,user ):
        """Charge one failed attempt against both the credential and the account."""
        max_attempts =settings .BIOMETRIC_SETTINGS .get ('MAX_FAILED_ATTEMPTS',5 )
        BiometricProfile .objects .filter (pk =profile .pk ).update (
        failed_attempts =F ('failed_attempts')+1 )
        user .failed_login_attempts +=1
        if user .failed_login_attempts >=max_attempts :
        # lock_account() persists locked_until and failed_login_attempts together.
            user .lock_account ()
        else :
            user .save (update_fields =['failed_login_attempts'])


class ChangePasswordSerializer (serializers .Serializer ):
    """Serializer for password change."""
    old_password =serializers .CharField (write_only =True )
    new_password =serializers .CharField (write_only =True )
    confirm_password =serializers .CharField (write_only =True )

    def validate_old_password (self ,value ):
        user =self .context ['request'].user 
        if not user .check_password (value ):
            raise serializers .ValidationError ('كلمة المرور القديمة غير صحيحة')
        return value 

    def validate (self ,attrs ):
        if attrs ['new_password']!=attrs ['confirm_password']:
            raise serializers .ValidationError ({'confirm_password':'كلمتا المرور غير متطابقتين'})
        try :
            password_validation .validate_password (attrs ['new_password'])
        except ValidationError as e :
            raise serializers .ValidationError ({'new_password':list (e .messages )})
        return attrs 

    def save (self ):
        user =self .context ['request'].user 
        user .set_password (self .validated_data ['new_password'])
        user .save ()
        return user 


        # ---------------------------------------------------------------------------
        # Password reset (forgot password) — anonymous flow, see accounts/views.py
        # ---------------------------------------------------------------------------
class PasswordResetRequestSerializer (serializers .Serializer ):
    """Email body for POST /auth/password/reset/ (anonymous)."""
    email =serializers .EmailField ()


class PasswordResetConfirmSerializer (serializers .Serializer ):
    """Body for POST /auth/password/reset/confirm/ (uid + token + new password)."""
    uid =serializers .CharField ()
    token =serializers .CharField ()
    new_password =serializers .CharField (write_only =True )
    confirm_password =serializers .CharField (write_only =True )

    def validate (self ,attrs ):
        if attrs ['new_password']!=attrs ['confirm_password']:
            raise serializers .ValidationError ({'confirm_password':'كلمتا المرور غير متطابقتين'})
        try :
            password_validation .validate_password (attrs ['new_password'])
        except ValidationError as e :
            raise serializers .ValidationError ({'new_password':list (e .messages )})
        return attrs 
