"""
Audit log model for tracking all security events.
"""
import uuid
from django .db import models ,transaction ,connection
from django .utils .translation import gettext_lazy as _
from django .conf import settings
from django .utils import timezone
import hashlib
import hmac
import json

GENESIS_HASH ='GENESIS'

# Arbitrary but stable identifier for the Postgres advisory lock that serialises
# appends to the hash chain. Any constant works as long as every process uses the
# same one.
_CHAIN_LOCK_ID =7326041


def audit_hmac_key ():
    """Key used to sign audit rows.

    A dedicated AUDIT_LOG_HMAC_KEY is preferred so that leaking SECRET_KEY does not
    also hand over the ability to forge audit history; SECRET_KEY is the fallback so
    an existing deployment keeps signing instead of silently doing nothing.
    """
    key =getattr (settings ,'AUDIT_LOG_HMAC_KEY','')or settings .SECRET_KEY
    return key .encode ('utf-8')if isinstance (key ,str )else key


def _lock_chain ():
    """Serialise chain appends.

    select_for_update() on the tail row is not sufficient: under READ COMMITTED two
    writers both re-read the same tail and chain onto it, forking the chain. A
    Postgres advisory lock is a real mutex held for the length of the transaction.
    Other backends fall back to locking the tail row, which narrows the window
    without closing it — verify_chain() reports any fork that still slips through.
    """
    if connection .vendor =='postgresql':
        with connection .cursor ()as cursor :
            cursor .execute ('SELECT pg_advisory_xact_lock(%s)',[_CHAIN_LOCK_ID ])
        return
    try :
        AuditLog .objects .select_for_update ().order_by ('-timestamp','-id').only ('id').first ()
    except Exception :
        # sqlite has no row-level locks; nothing to acquire.
        pass


class AuditLog (models .Model ):
    """
    Audit log for all security-relevant actions.
    Required for HIPAA compliance and DevSecOps monitoring.
    """

    class EventType (models .TextChoices ):
    # Authentication events
        LOGIN_SUCCESS ='LOGIN_SUCCESS',_ ('تسجيل دخول ناجح')
        LOGIN_FAILED ='LOGIN_FAILED',_ ('فشل تسجيل الدخول')
        LOGOUT ='LOGOUT',_ ('تسجيل خروج')
        BIOMETRIC_LOGIN_SUCCESS ='BIOMETRIC_LOGIN_SUCCESS',_ ('دخول بيوميتري ناجح')
        BIOMETRIC_ENROLLMENT ='BIOMETRIC_ENROLLMENT',_ ('تسجيل بصمة')
        BIOMETRIC_CHALLENGE_REQUESTED ='BIOMETRIC_CHALLENGE_REQUESTED',_ ('طلب تحدي بيوميتري')
        BIOMETRIC_REVOKED ='BIOMETRIC_REVOKED',_ ('إلغاء بصمة')
        PASSWORD_CHANGED ='PASSWORD_CHANGED',_ ('تغيير كلمة المرور')

        # Authorization events
        PERMISSION_GRANTED ='PERMISSION_GRANTED',_ ('منح صلاحية')
        PERMISSION_MODIFIED ='PERMISSION_MODIFIED',_ ('تعديل صلاحية')
        PERMISSION_REVOKED ='PERMISSION_REVOKED',_ ('سحب صلاحية')
        MEMBERSHIP_CANCELLED ='MEMBERSHIP_CANCELLED',_ ('إلغاء عضوية')

        # Channel events
        CHANNEL_CREATED ='CHANNEL_CREATED',_ ('إنشاء قناة')
        CHANNEL_CLOSED ='CHANNEL_CLOSED',_ ('إغلاق قناة')
        CHANNEL_MESSAGE_SENT ='CHANNEL_MESSAGE_SENT',_ ('إرسال رسالة في قناة')

        # Data access events
        PATIENT_DATA_ACCESSED ='PATIENT_DATA_ACCESSED',_ ('الوصول لبيانات مريض')
        MEDICAL_RECORD_CREATED ='MEDICAL_RECORD_CREATED',_ ('إنشاء سجل طبي')

        # Security tool events
        PORT_SCAN_EXECUTED ='PORT_SCAN_EXECUTED',_ ('تنفيذ مسح منافذ')
        VULN_SCAN_EXECUTED ='VULN_SCAN_EXECUTED',_ ('تنفيذ فحص ثغرات')
        WAF_BLOCKED ='WAF_BLOCKED',_ ('حظر WAF')

        # Invitation events
        INVITATION_SENT ='INVITATION_SENT',_ ('إرسال دعوة')
        INVITATION_ACCEPTED ='INVITATION_ACCEPTED',_ ('قبول دعوة')
        INVITATION_REJECTED ='INVITATION_REJECTED',_ ('رفض دعوة')

        # User management
        USER_DEACTIVATED ='USER_DEACTIVATED',_ ('إلغاء تفعيل مستخدم')

        # Two-factor authentication
        MFA_ENABLED ='MFA_ENABLED',_ ('تفعيل التحقق بخطوتين')
        MFA_DISABLED ='MFA_DISABLED',_ ('تعطيل التحقق بخطوتين')
        MFA_LOGIN_SUCCESS ='MFA_LOGIN_SUCCESS',_ ('دخول ناجح بالتحقق بخطوتين')
        MFA_LOGIN_FAILED ='MFA_LOGIN_FAILED',_ ('فشل التحقق بخطوتين')

        # Password reset flow
        PASSWORD_RESET_REQUESTED ='PASSWORD_RESET_REQUESTED',_ ('طلب استعادة كلمة المرور')
        PASSWORD_RESET_COMPLETED ='PASSWORD_RESET_COMPLETED',_ ('إتمام استعادة كلمة المرور')

        # Enhanced Audit Events
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

        # Generic Data Mutations
        DATA_CREATED ='DATA_CREATED',_ ('إنشاء بيانات')
        DATA_MODIFIED ='DATA_MODIFIED',_ ('تعديل بيانات')
        DATA_DELETED ='DATA_DELETED',_ ('حذف بيانات')

        # Events the application already emitted without declaring them here.
        # A value outside `choices` still saves — CharField.choices is not a DB
        # constraint — so these logged fine but showed up raw in the admin, broke
        # get_event_type_display() and were invisible to every list_filter and
        # report built from the choices. The code is the source of truth for what
        # events exist, so the enum now matches it.
        DATA_ACCESSED ='DATA_ACCESSED',_ ('قراءة بيانات')
        SYSTEM_EVENT ='SYSTEM_EVENT',_ ('حدث نظام')
        LOGIN_CHALLENGE ='LOGIN_CHALLENGE',_ ('طلب تحقق إضافي عند الدخول')
        USER_ACTIVATED ='USER_ACTIVATED',_ ('تفعيل مستخدم')

        BASIN_CREATED ='BASIN_CREATED',_ ('إنشاء حوض صحي')
        BASIN_UPDATED ='BASIN_UPDATED',_ ('تعديل حوض صحي')
        BASIN_DELETED ='BASIN_DELETED',_ ('حذف حوض صحي')
        BASIN_MODULE_TOGGLED ='BASIN_MODULE_TOGGLED',_ ('تفعيل/تعطيل وحدة في حوض')
        BASIN_TYPE_DEFAULTS_APPLIED ='BASIN_TYPE_DEFAULTS_APPLIED',_ ('تطبيق إعدادات نوع الحوض')

        APPOINTMENT_CREATED ='APPOINTMENT_CREATED',_ ('إنشاء موعد')
        APPOINTMENT_CONFIRMED ='APPOINTMENT_CONFIRMED',_ ('تأكيد موعد')
        APPOINTMENT_COMPLETED ='APPOINTMENT_COMPLETED',_ ('إكمال موعد')
        APPOINTMENT_CANCELLED ='APPOINTMENT_CANCELLED',_ ('إلغاء موعد')
        APPOINTMENT_DELETED ='APPOINTMENT_DELETED',_ ('حذف موعد')

        PRESCRIPTION_DISPENSED ='PRESCRIPTION_DISPENSED',_ ('صرف وصفة طبية')
        PHARMACY_STOCK_CHANGE ='PHARMACY_STOCK_CHANGE',_ ('تغيير مخزون الصيدلية')
        INVOICE_PAID ='INVOICE_PAID',_ ('سداد فاتورة')
        FHIR_PATIENT_EXPORT ='FHIR_PATIENT_EXPORT',_ ('تصدير مريض بصيغة FHIR')

        AI_ASSISTANT_QUERY ='AI_ASSISTANT_QUERY',_ ('استعلام المساعد الذكي')
        AI_ASSISTANT_FAILED ='AI_ASSISTANT_FAILED',_ ('فشل المساعد الذكي')
        AI_INTERACTION_CHECKED ='AI_INTERACTION_CHECKED',_ ('فحص تداخلات دوائية آلي')
        AI_INTERACTION_FAILED ='AI_INTERACTION_FAILED',_ ('فشل فحص التداخلات الدوائية')
        AI_SUMMARY_GENERATED ='AI_SUMMARY_GENERATED',_ ('توليد ملخص ذكي')
        AI_SUMMARY_FAILED ='AI_SUMMARY_FAILED',_ ('فشل توليد الملخص الذكي')
        AI_IMAGE_ANALYSIS ='AI_IMAGE_ANALYSIS',_ ('تحليل صورة طبية')
        AI_IMAGE_ANALYSIS_FAILED ='AI_IMAGE_ANALYSIS_FAILED',_ ('فشل تحليل صورة طبية')
        AI_STRUCTURE_NOTE_FAILED ='AI_STRUCTURE_NOTE_FAILED',_ ('فشل هيكلة ملاحظة سريرية')
        AI_TRIAGE_FAILED ='AI_TRIAGE_FAILED',_ ('فشل التقييم الآلي للخطورة')
        # Default of apps/ai/views.py::_upstream_failure — reached by any AI view
        # that calls it without naming its own event type.
        AI_REQUEST_FAILED ='AI_REQUEST_FAILED',_ ('فشل طلب ذكاء اصطناعي')

        # apps/core/views.py — offline sync is deliberately not implemented, and
        # every attempt is recorded because the client believes it saved data.
        OFFLINE_SYNC_REJECTED ='OFFLINE_SYNC_REJECTED',_ ('رفض مزامنة دون اتصال')

        MONTHLY_REPORT_EMAILED ='MONTHLY_REPORT_EMAILED',_ ('إرسال التقرير الشهري')
        SCHEDULED_REPORT_SENT ='SCHEDULED_REPORT_SENT',_ ('إرسال تقرير مجدول')
        TEST_EMAIL_SENT ='TEST_EMAIL_SENT',_ ('إرسال بريد اختباري')

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

    # Enhanced Device Fingerprint Fields
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
    
    hash = models.CharField(_('التوقيع التشفيري'), max_length=64, blank=True, null=True, editable=False)
    previous_hash = models.CharField(_('توقيع السجل السابق'), max_length=64, blank=True, null=True, editable=False)

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

    def canonical_payload (self ):
        """The exact bytes the signature covers.

        Two details matter. First, every field a tamperer would want to rewrite is
        included — changing the actor, the IP or the path has to invalidate the
        signature, not just changing the event type. Second, the fields are joined
        with an ASCII unit separator instead of '-': with '-' as the delimiter, a
        value that itself contains a dash can shift content across field boundaries
        and let two different records produce the same digest.
        """
        try :
            details_str =json .dumps (self .details ,sort_keys =True ,separators =(',',':'),default =str )
        except (TypeError ,ValueError ):
            details_str =str (self .details )

        parts =[
        str (self .id ),
        str (self .user_id )if self .user_id else '',
        self .event_type or '',
        self .severity or '',
        str (self .ip_address )if self .ip_address else '',
        self .path or '',
        self .method or '',
        self .device_fingerprint or '',
        self .session_id or '',
        self .timestamp .isoformat ()if self .timestamp else '',
        self .previous_hash or '',
        details_str ,
        ]
        return '\x1f'.join (parts ).encode ('utf-8')

    def generate_hash (self ):
        """Keyed HMAC-SHA256 over canonical_payload().

        The previous implementation was a bare sha256 over public column values,
        which proves nothing: anyone able to edit a row could recompute its digest
        and every digest after it, so the chain was evidence against accidental
        corruption only. An HMAC cannot be recomputed without the key, and the key
        lives in the environment rather than the database. hexdigest() is 64
        characters either way, so the existing column widths still fit.
        """
        return hmac .new (audit_hmac_key (),self .canonical_payload (),hashlib .sha256 ).hexdigest ()

    def legacy_hash (self ):
        """Reproduce the pre-HMAC digest byte for byte.

        Rows written before signing was keyed can then be reported as 'legacy'
        rather than as tampering, which keeps a verification run readable.
        """
        data_string =f"{self .user_id }-{self .event_type }-{self .severity }-{self .ip_address }-{self .timestamp }-{self .previous_hash }"
        try :
            data_string +=f"-{json .dumps (self .details ,sort_keys =True )}"
        except Exception :
            data_string +=f"-{self .details }"
        return hashlib .sha256 (data_string .encode ('utf-8')).hexdigest ()

    def save (self ,*args ,**kwargs ):
        # `not self.pk` was the old test for "is this a new row", but `id` is a
        # UUIDField with default=uuid.uuid4, so pk is populated in __init__ and the
        # test was never true. The entire chaining block was dead code and every
        # row landed with hash and previous_hash NULL. _state.adding is the check
        # that actually distinguishes an insert from an update.
        if not self ._state .adding or self .hash :
            return super ().save (*args ,**kwargs )

        with transaction .atomic ():
            _lock_chain ()

            # Deliberately the last *signed* row, not the last row. Older unsigned
            # rows must not reset the chain back to GENESIS and orphan everything
            # already signed above them.
            last =(AuditLog .objects
            .exclude (hash__isnull =True ).exclude (hash ='')
            .order_by ('-timestamp','-id').only ('hash').first ())
            self .previous_hash =last .hash if last else GENESIS_HASH

            super ().save (*args ,**kwargs )

            # timestamp is auto_now_add, so its value only exists after the INSERT —
            # hence signing in a second write. Both are in one transaction, so a
            # crash in between cannot leave an unsigned row behind.
            self .hash =self .generate_hash ()
            AuditLog .objects .filter (pk =self .pk ).update (
            hash =self .hash ,previous_hash =self .previous_hash
            )

    @classmethod
    def verify_chain (cls ,since =None ,limit =None ):
        """Recompute every signature and re-walk the links.

        Returns a summary dict: counts plus a list of problems, each naming the row
        and what is wrong with it. Tamper evidence that nothing ever reads is
        decoration, so this is the routine the verify_audit_chain management command
        calls — wire it into a scheduled job to get an actual alert.
        """
        qs =cls .objects .order_by ('timestamp','id')
        if since is not None :
            qs =qs .filter (timestamp__gte =since )
        if limit :
            qs =qs [:limit ]

        result ={'checked':0 ,'signed':0 ,'legacy':0 ,'unsigned':0 ,'problems':[]}
        # Starting mid-chain means the expected predecessor is unknown, so link
        # checking begins at the second row of the window instead of demanding
        # GENESIS.
        expected_previous =GENESIS_HASH if since is None else None

        for row in qs .iterator ():
            result ['checked']+=1

            if not row .hash :
                result ['unsigned']+=1
                continue

            if hmac .compare_digest (row .generate_hash (),row .hash ):
                result ['signed']+=1
            elif hmac .compare_digest (row .legacy_hash (),row .hash ):
                result ['legacy']+=1
            else :
                result ['problems'].append ({
                'id':str (row .id ),
                'timestamp':row .timestamp .isoformat ()if row .timestamp else None ,
                'error':'signature_mismatch',
                })

            if expected_previous is not None and (row .previous_hash or '')!=expected_previous :
                result ['problems'].append ({
                'id':str (row .id ),
                'timestamp':row .timestamp .isoformat ()if row .timestamp else None ,
                'error':'broken_link',
                'expected_previous':expected_previous ,
                'found_previous':row .previous_hash ,
                })

            expected_previous =row .hash

        result ['ok']=not result ['problems']
        return result

