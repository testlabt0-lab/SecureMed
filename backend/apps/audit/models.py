"""
Audit log model for tracking all security events.
"""
import uuid 
from django .db import models 
from django .utils .translation import gettext_lazy as _ 
from django .conf import settings 
from django .utils import timezone 


class AuditLog (models .Model ):
    """
    Audit log for all security-relevant actions.
    Required for HIPAA compliance and DevSecOps monitoring.
    """

    class EventType (models .TextChoices ):
    # Comment_127
        LOGIN_SUCCESS ='LOGIN_SUCCESS',_ ('تسجيل دخول ناجح')
        LOGIN_FAILED ='LOGIN_FAILED',_ ('فشل تسجيل الدخول')
        LOGOUT ='LOGOUT',_ ('تسجيل خروج')
        BIOMETRIC_LOGIN_SUCCESS ='BIOMETRIC_LOGIN_SUCCESS',_ ('دخول بيوميتري ناجح')
        BIOMETRIC_ENROLLMENT ='BIOMETRIC_ENROLLMENT',_ ('تسجيل بصمة')
        BIOMETRIC_CHALLENGE_REQUESTED ='BIOMETRIC_CHALLENGE_REQUESTED',_ ('طلب تحدي بيوميتري')
        BIOMETRIC_REVOKED ='BIOMETRIC_REVOKED',_ ('إلغاء بصمة')
        PASSWORD_CHANGED ='PASSWORD_CHANGED',_ ('تغيير كلمة المرور')

        # Comment_128
        PERMISSION_GRANTED ='PERMISSION_GRANTED',_ ('منح صلاحية')
        PERMISSION_MODIFIED ='PERMISSION_MODIFIED',_ ('تعديل صلاحية')
        PERMISSION_REVOKED ='PERMISSION_REVOKED',_ ('سحب صلاحية')
        MEMBERSHIP_CANCELLED ='MEMBERSHIP_CANCELLED',_ ('إلغاء عضوية')

        # Comment_129
        CHANNEL_CREATED ='CHANNEL_CREATED',_ ('إنشاء قناة')
        CHANNEL_CLOSED ='CHANNEL_CLOSED',_ ('إغلاق قناة')
        CHANNEL_MESSAGE_SENT ='CHANNEL_MESSAGE_SENT',_ ('إرسال رسالة في قناة')

        # Comment_130
        PATIENT_DATA_ACCESSED ='PATIENT_DATA_ACCESSED',_ ('الوصول لبيانات مريض')
        MEDICAL_RECORD_CREATED ='MEDICAL_RECORD_CREATED',_ ('إنشاء سجل طبي')

        # Comment_131
        PORT_SCAN_EXECUTED ='PORT_SCAN_EXECUTED',_ ('تنفيذ مسح منافذ')
        VULN_SCAN_EXECUTED ='VULN_SCAN_EXECUTED',_ ('تنفيذ فحص ثغرات')
        WAF_BLOCKED ='WAF_BLOCKED',_ ('حظر WAF')

        # Comment_132
        INVITATION_SENT ='INVITATION_SENT',_ ('إرسال دعوة')
        INVITATION_ACCEPTED ='INVITATION_ACCEPTED',_ ('قبول دعوة')
        INVITATION_REJECTED ='INVITATION_REJECTED',_ ('رفض دعوة')

        # Comment_133
        USER_DEACTIVATED ='USER_DEACTIVATED',_ ('إلغاء تفعيل مستخدم')

        # Comment_134
        MFA_ENABLED ='MFA_ENABLED',_ ('تفعيل التحقق بخطوتين')
        MFA_DISABLED ='MFA_DISABLED',_ ('تعطيل التحقق بخطوتين')
        MFA_LOGIN_SUCCESS ='MFA_LOGIN_SUCCESS',_ ('دخول ناجح بالتحقق بخطوتين')
        MFA_LOGIN_FAILED ='MFA_LOGIN_FAILED',_ ('فشل التحقق بخطوتين')

        # Comment_135
        PASSWORD_RESET_REQUESTED ='PASSWORD_RESET_REQUESTED',_ ('طلب استعادة كلمة المرور')
        PASSWORD_RESET_COMPLETED ='PASSWORD_RESET_COMPLETED',_ ('إتمام استعادة كلمة المرور')

        # Comment_136
        DEVICE_BLOCKED ='DEVICE_BLOCKED',_ ('حظر جهاز')
        SUSPICIOUS_ACTIVITY ='SUSPICIOUS_ACTIVITY',_ ('نشاط مشبوه')
        SESSION_HIJACK_DETECTED ='SESSION_HIJACK_DETECTED',_ ('اكتشاف سرقة جلسة')
        DATA_EXPORT ='DATA_EXPORT',_ ('تصدير بيانات')
        BULK_DELETE ='BULK_DELETE',_ ('حذف جماعي')
        CONFIG_CHANGED ='CONFIG_CHANGED',_ ('تغيير إعدادات')
        BACKUP_CREATED ='BACKUP_CREATED',_ ('إنشاء نسخة احتياطية')
        BACKUP_RESTORED ='BACKUP_RESTORED',_ ('استعادة نسخة احتياطية')
        FILE_UPLOADED ='FILE_UPLOADED',_ ('رفع ملف')
        FILE_DOWNLOADED ='FILE_DOWNLOADED',_ ('تحميل ملف')

        # Comment_137
        DATA_CREATED ='DATA_CREATED',_ ('إنشاء بيانات')
        DATA_MODIFIED ='DATA_MODIFIED',_ ('تعديل بيانات')
        DATA_DELETED ='DATA_DELETED',_ ('حذف بيانات')

    class Severity (models .TextChoices ):
        INFO ='INFO',_ ('معلومة')
        WARNING ='WARNING',_ ('تحذير')
        CRITICAL ='CRITICAL',_ ('حرج')

    id =models .UUIDField (primary_key =True ,default =uuid .uuid4 ,editable =False )
    user =models .ForeignKey (
    settings .AUTH_USER_MODEL ,
    on_delete =models .SET_NULL ,null =True ,
    related_name ='audit_logs',
    verbose_name =_ ('المستخدم')
    )
    event_type =models .CharField (
    _ ('نوع الحدث'),max_length =40 ,
    choices =EventType .choices ,db_index =True 
    )
    severity =models .CharField (
    _ ('الخطورة'),max_length =10 ,
    choices =Severity .choices ,default =Severity .INFO 
    )
    ip_address =models .GenericIPAddressField (_ ('عنوان IP'),null =True ,blank =True )
    user_agent =models .TextField (_ ('User Agent'),blank =True )
    path =models .CharField (_ ('المسار'),max_length =255 ,blank =True )
    method =models .CharField (_ ('الطريقة'),max_length =10 ,blank =True )

    # Comment_138
    mac_address =models .CharField (_ ('عنوان MAC'),max_length =100 ,blank =True )
    device_fingerprint =models .CharField (_ ('بصمة الجهاز'),max_length =255 ,blank =True ,db_index =True )
    hostname =models .CharField (_ ('اسم الجهاز'),max_length =255 ,blank =True )
    os_info =models .CharField (_ ('نظام التشغيل'),max_length =255 ,blank =True )
    browser_info =models .CharField (_ ('المتصفح'),max_length =255 ,blank =True )
    screen_resolution =models .CharField (_ ('دقة الشاشة'),max_length =50 ,blank =True )
    timezone_offset =models .CharField (_ ('فرق التوقيت'),max_length =50 ,blank =True )
    language =models .CharField (_ ('اللغة'),max_length =50 ,blank =True )
    session_id =models .CharField (_ ('معرف الجلسة'),max_length =255 ,blank =True ,db_index =True )
    geo_location =models .CharField (_ ('الموقع الجغرافي'),max_length =255 ,blank =True )
    risk_score =models .FloatField (_ ('درجة المخاطرة'),default =0.0 )

    details =models .JSONField (_ ('التفاصيل'),default =dict )
    timestamp =models .DateTimeField (_ ('الوقت'),auto_now_add =True ,db_index =True )

    class Meta :
        verbose_name =_ ('سجل تدقيق')
        verbose_name_plural =_ ('سجلات التدقيق')
        ordering =['-timestamp']
        indexes =[
        models .Index (fields =['event_type','-timestamp']),
        models .Index (fields =['user','-timestamp']),
        models .Index (fields =['severity','-timestamp']),
        ]

    def __str__ (self ):
        return f'{self .get_event_type_display ()} - {self .timestamp }'
