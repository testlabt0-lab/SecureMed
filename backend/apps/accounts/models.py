"""
User models for SecureMed.

Implements:
- Custom User model with role-based access
- Biometric authentication storage (security requirement #4: fingerprint login)
- Per-channel role assignment (DV requirement: single role per user per channel)
"""
import uuid 
from django .contrib .auth .models import AbstractUser ,BaseUserManager 
from django .db import models 
from django .utils .translation import gettext_lazy as _ 
from django .utils import timezone 
from django .core .exceptions import ValidationError 

from apps .security .crypto import encrypt_field ,decrypt_field 


class UserManager (BaseUserManager ):
    """Custom manager for User model."""

    def create_user (self ,email ,password =None ,**extra_fields ):
        if not email :
            raise ValueError (_ ('Email is required'))
        email =self .normalize_email (email )
        user =self .model (email =email ,**extra_fields )
        user .set_password (password )
        user .save (using =self ._db )
        return user 

    def create_superuser (self ,email ,password =None ,**extra_fields ):
        extra_fields .setdefault ('is_staff',True )
        extra_fields .setdefault ('is_superuser',True )
        extra_fields .setdefault ('is_active',True )
        extra_fields .setdefault ('role','SUPER_ADMIN')
        if extra_fields .get ('is_staff')is not True :
            raise ValueError (_ ('Superuser must have is_staff=True.'))
        if extra_fields .get ('is_superuser')is not True :
            raise ValueError (_ ('Superuser must have is_superuser=True.'))
        return self .create_user (email ,password ,**extra_fields )


class User (AbstractUser ):
    """
    Custom user model with role-based access control.

    Implements the DV requirement: each user has exactly ONE system-level role
    (per-channel roles are managed through ChannelMembership).
    """

    class Role (models .TextChoices ):
        SUPER_ADMIN ='SUPER_ADMIN',_ ('مدير النظام')
        HOSPITAL_ADMIN ='HOSPITAL_ADMIN',_ ('مدير المستشفى')
        CENTER_ADMIN = 'CENTER_ADMIN', _('مدير مركز')
        DOCTOR ='DOCTOR',_ ('طبيب')
        NURSE ='NURSE',_ ('ممرض/ممرضة')
        LAB_TECH ='LAB_TECH',_ ('فني مختبر')
        PHARMACIST ='PHARMACIST',_ ('صيدلي')
        AUDITOR ='AUDITOR',_ ('مراجع أمني')
        PATIENT ='PATIENT',_ ('مريض')
        ACCOUNTANT = 'ACCOUNTANT', _('محاسب')
        RECEPTIONIST = 'RECEPTIONIST', _('موظف استقبال')

    id =models .UUIDField (primary_key =True ,default =uuid .uuid4 ,editable =False )
    username =None # Use email instead
    email =models .EmailField (_ ('البريد الإلكتروني'),unique =True ,db_index =True )
    full_name =models .CharField (_ ('الاسم الكامل'),max_length =255 ,db_index =True )
    phone =models .CharField (_ ('الهاتف'),max_length =20 ,blank =True )
    role =models .CharField (
    _ ('الدور'),max_length =20 ,choices =Role .choices ,default =Role .PATIENT ,db_index =True 
    )
    license_number =models .CharField (
    _ ('رقم الترخيص الطبي'),max_length =50 ,blank =True ,null =True 
    )
    department =models .CharField (_ ('القسم'),max_length =100 ,blank =True )
    specialization =models .CharField (_ ('التخصص'),max_length =100 ,blank =True )

    # Basin linkage (plan requirement: the system must be linked to basins)
    basin =models .ForeignKey (
    'basins.Basin',on_delete =models .PROTECT ,
    null =True ,blank =True ,
    related_name ='users',verbose_name =_ ('الحوض الصحي'),
    )

    # Security fields
    is_biometric_enabled =models .BooleanField (
    _ ('المصادقة البيومترية مفعلة'),default =False 
    )
    biometric_enrolled_at =models .DateTimeField (null =True ,blank =True )
    last_login_ip =models .GenericIPAddressField (null =True ,blank =True )
    failed_login_attempts =models .PositiveIntegerField (default =0 )
    locked_until =models .DateTimeField (null =True ,blank =True )
    mfa_secret =models .CharField (max_length =255 ,blank =True )# Encrypted

    # Two-factor authentication (TOTP)
    mfa_enabled =models .BooleanField (_ ('التحقق بخطوتين مفعل'),default =False )
    mfa_created_at =models .DateTimeField (null =True ,blank =True )

    # Audit fields
    created_at =models .DateTimeField (auto_now_add =True )
    updated_at =models .DateTimeField (auto_now =True )

    USERNAME_FIELD ='email'
    REQUIRED_FIELDS =['full_name','role']

    objects =UserManager ()

    class Meta :
        verbose_name =_ ('مستخدم')
        verbose_name_plural =_ ('المستخدمون')
        ordering =['-created_at']

    def __str__ (self ):
        return f'{self .full_name } ({self .get_role_display ()})'

    @property 
    def is_medical_staff (self ):
        return self .role in [
        self .Role .DOCTOR ,self .Role .NURSE ,
        self .Role .LAB_TECH ,self .Role .PHARMACIST 
        ]

    @property 
    def is_locked (self ):
        if self .locked_until and self .locked_until >timezone .now ():
            return True 
        return False 

    def lock_account (self ,minutes =None ):
        """Lock the account using exponential backoff based on failed attempts or explicit minutes."""
        if minutes is None :
        # Base lock time is 5 minutes, doubling each time after the 3rd attempt
            power =max (0 ,self .failed_login_attempts -3 )
            minutes =5 *(2 **power )
            # Max lock out time of 24 hours
            minutes =min (minutes ,1440 )

        self .locked_until =timezone .now ()+timezone .timedelta (minutes =minutes )
        self .save (update_fields =['locked_until','failed_login_attempts'])

    def reset_failed_attempts (self ):
        """Reset failed login attempts on successful login."""
        self .failed_login_attempts =0 
        self .locked_until =None 
        self .save (update_fields =['failed_login_attempts','locked_until'])


class BiometricProfile (models .Model ):
    """One public-key credential, enrolled on one device.

    Security requirement #4: تسجيل الدخول بالبصمة + الاعتماد على البصمة

    The server stores only the **public** key. Logging in means signing a
    server-issued, single-use challenge with a private key that lives in the
    device's secure hardware (Android Keystore / Secure Enclave / platform
    authenticator) and is released only after the biometric prompt succeeds.
    Verification happens in ``apps.security.crypto``.

    Until this was rebuilt, the model instead stored ``biometric_hash``: a salted
    hash of a "biometric template" string the client sent on *every* login. That
    made the template a shared secret — a password that the user cannot ever
    change — and it meant the server could not distinguish a real fingerprint
    from any client that had once seen the string. ``biometric_hash``, ``salt``
    and ``private_key_encrypted`` are retained so that existing rows migrate
    cleanly, but nothing in the authentication path reads or writes them.
    """

    id =models .UUIDField (primary_key =True ,default =uuid .uuid4 ,editable =False )
    user =models .ForeignKey (
    User ,on_delete =models .CASCADE ,
    related_name ='biometric_profiles',
    verbose_name =_ ('المستخدم')
    )
    device_id =models .CharField (_ ('معرف الجهاز'),max_length =255 )
    device_name =models .CharField (_ ('اسم الجهاز'),max_length =255 ,blank =True )
    platform =models .CharField (
    _ ('المنصة'),max_length =20 ,
    choices =[('ANDROID','Android'),('IOS','iOS'),('WEB','Web')]
    )

    # Deprecated by the WebAuthn rebuild — see the class docstring. Kept nullable
    # so old rows survive; new enrollments leave both empty.
    biometric_hash =models .TextField (_ ('الهاش البيوميتري المشفر'),blank =True ,default ='')
    salt =models .CharField (_ ('الملح'),max_length =64 ,blank =True ,default ='')

    # SPKI PEM of the enrolled public key. The matching private key never leaves
    # the device. `private_key_encrypted` is a leftover from the old design and
    # must stay empty: a relying party that holds the private key has given up
    # the only property that makes this stronger than a password.
    public_key =models .TextField (_ ('المفتاح العام'),blank =True )
    private_key_encrypted =models .TextField (_ ('المفتاح الخاص المشفر'),blank =True )

    # PublicKeyCredential.rawId, base64url. Set for WEB (WebAuthn) credentials and
    # returned in allowCredentials so the browser knows which key to use; empty on
    # native platforms, where device_id identifies the credential on its own.
    credential_id =models .TextField (_ ('معرف بيانات الاعتماد'),blank =True ,default ='')

    # authenticatorData signature counter, used for cloned-credential detection.
    # Platform authenticators usually report 0 forever, so a 0 here is normal.
    sign_count =models .PositiveBigIntegerField (_ ('عدّاد التوقيع'),default =0 )

    is_active =models .BooleanField (_ ('نشط'),default =True )
    last_used =models .DateTimeField (null =True ,blank =True )
    failed_attempts =models .PositiveIntegerField (default =0 )

    created_at =models .DateTimeField (auto_now_add =True )
    updated_at =models .DateTimeField (auto_now =True )

    class Meta :
        verbose_name =_ ('الملف البيوميتري')
        verbose_name_plural =_ ('الملفات البيومترية')
        unique_together =['user','device_id']
        indexes =[
        models .Index (fields =['user','device_id']),
        models .Index (fields =['is_active']),
        ]

    def __str__ (self ):
        return f'{self .user .full_name } - {self .platform } ({self .device_name })'


class BiometricChallenge (models .Model ):
    """A single-use, short-lived nonce for one biometric login attempt.

    `challenge` is 32 random bytes, base64url. The server keeps no "expected
    response": the proof is a signature over these bytes, checked against the
    public key on `profile`. `expected_response` is a leftover from the previous
    design and stays empty.
    """

    id =models .UUIDField (primary_key =True ,default =uuid .uuid4 ,editable =False )
    user =models .ForeignKey (
    User ,on_delete =models .CASCADE ,
    related_name ='biometric_challenges'
    )
    # Bound to the device that asked for it. Without this the challenge was bound
    # to the user only, so a credential enrolled on device A could answer a
    # challenge issued for device B — the "per-device binding" the old docstring
    # claimed did not exist anywhere in the flow.
    profile =models .ForeignKey (
    'accounts.BiometricProfile',on_delete =models .CASCADE ,
    related_name ='challenges',null =True ,blank =True
    )
    challenge =models .TextField (_ ('التحدي'))
    expected_response =models .TextField (_ ('الرد المتوقع المشفر'),blank =True ,default ='')
    expires_at =models .DateTimeField (_ ('تنتهي في'))
    used =models .BooleanField (default =False )
    created_at =models .DateTimeField (auto_now_add =True )

    class Meta :
        ordering =['-created_at']
        indexes =[models .Index (fields =['user','used','expires_at'])]

    @property
    def is_valid (self ):
        return (
        not self .used and
        self .expires_at >timezone .now ()
        )

    def claim (self ):
        """Consume the challenge, or return False if someone else already did.

        A single UPDATE ... WHERE used = false decides the winner in the database,
        so two requests replaying the same challenge_id concurrently cannot both
        get past it. Reading `is_valid` and then calling `mark_used()` — what the
        login path used to do — leaves exactly that window open.
        """
        claimed =type (self ).objects .filter (
        pk =self .pk ,used =False ,expires_at__gt =timezone .now ()
        ).update (used =True )
        if claimed :
            self .used =True
        return bool (claimed )

    def mark_used (self ):
        self .used =True
        self .save (update_fields =['used'])


class RolePermission (models .Model ):
    """تجاوز ديناميكي لصلاحية دور — إدارة الصلاحيات (متطلب د. مجد).

    الأدوار الثابتة (``User.Role``) تحدد الافتراضي في
    ``apps.accounts.permissions.DEFAULT_ROLE_PERMISSIONS``، وهذا الموديل
    يسمح للإدارة بتعديل حكم أي دور على أي صلاحية من الواجهة دون نشر كود:
    سجل موجود هنا يسري فوراً، وغيابه يعني تطبيق الافتراضي.

    لا يمكن قصر SUPER_ADMIN على صلاحية: ``effective_allows`` تعيده دائماً
    مفعلاً حتى لو سُجل تجاوز ضده — منع الإدارة من إغلاقها لنفسها.
    """

    id =models .UUIDField (primary_key =True ,default =uuid .uuid4 ,editable =False )
    role =models .CharField (
    _ ('الدور'),max_length =20 ,choices =User .Role .choices ,db_index =True
    )
    permission =models .CharField (_ ('الصلاحية'),max_length =100 ,db_index =True )
    allowed =models .BooleanField (_ ('مسموح'),default =True )
    updated_by =models .ForeignKey (
    User ,on_delete =models .SET_NULL ,null =True ,blank =True ,
    related_name ='role_permission_changes',verbose_name =_ ('آخر تعديل بواسطة')
    )
    created_at =models .DateTimeField (auto_now_add =True )
    updated_at =models .DateTimeField (auto_now =True )

    class Meta :
        verbose_name =_ ('صلاحية دور')
        verbose_name_plural =_ ('صلاحيات الأدوار')
        unique_together =['role','permission']
        ordering =['role','permission']

    def __str__ (self ):
        state ='مسموح'if self .allowed else 'ممنوع'
        return f'{self .role }: {self .permission } ({state })'

    def clean (self ):
        from apps .accounts .permissions import _PERMISSIONS_BY_CODE
        if self .permission not in _PERMISSIONS_BY_CODE :
            raise ValidationError (_ ('صلاحية غير معروفة في الكتالوج'))

