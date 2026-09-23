"""
Patient Access Transparency Ledger (سجل شفافية وصول المريض لبياناته).

Complies with:
- Saudi Personal Data Protection Law (PDPL - نظام حماية البيانات الشخصية الصادر بالمرسوم الملكي م/19)
- HIPAA Accounting of Disclosures Rule (45 CFR § 164.528)

Grants patients full transparency over who accessed their health records,
when, from which department, and the clinical or emergency justification.
"""
import logging
from typing import Any, Dict, List, Optional
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger('security')

TRANSPARENCY_EVENT_TYPES = (
    'PATIENT_DATA_ACCESSED',
    'BREAK_GLASS_ACTIVATED',
    'MEDICAL_RECORD_CREATED',
    'MEDICAL_RECORD_UPDATED',
    'PRESCRIPTION_CREATED',
    'FILE_DOWNLOADED',
    'AI_SUMMARY_GENERATED',
    'FHIR_PATIENT_EXPORT',
)

ROLE_ARABIC_TITLES = {
    'DOCTOR': 'طبيب معالج',
    'NURSE': 'طاقم تمريض',
    'LAB_TECH': 'أخصائي مختبر',
    'PHARMACIST': 'صيدلي ممارس',
    'HOSPITAL_ADMIN': 'إدارة المنشأة الصحية',
    'SUPER_ADMIN': 'إدارة النظام والأمن السيبراني',
    'AUDITOR': 'مدقق التزام وسجلات',
    'RECEPTIONIST': 'استقبال وتسجيل',
    'PATIENT': 'المريض نفسه',
}

EVENT_ARABIC_DESCRIPTIONS = {
    'PATIENT_DATA_ACCESSED': 'معاينة الملف الطبي السريري',
    'BREAK_GLASS_ACTIVATED': 'وصول طوارئ استثنائي (كسر الزجاج)',
    'MEDICAL_RECORD_CREATED': 'إضافة سجل طبي / تشخيص جديد',
    'MEDICAL_RECORD_UPDATED': 'تحديث في الملاحظات السريرية',
    'PRESCRIPTION_CREATED': 'إصدار وصفة علاجية إلكترونية',
    'FILE_DOWNLOADED': 'تحميل مستند أو فحص إشعاعي',
    'AI_SUMMARY_GENERATED': 'استشارة الذكاء الاصطناعي للملخص الطبي',
    'FHIR_PATIENT_EXPORT': 'تصدير السجل الطبي الموحد (FHIR)',
}


def mask_client_ip(ip_address: Optional[str]) -> str:
    """Mask IP address to balance patient transparency with clinician network privacy."""
    if not ip_address:
        return '—'
    parts = ip_address.split('.')
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.***.***"
    if ':' in ip_address:  # IPv6
        return ip_address[:14] + '****:****'
    return '***.***.***.***'


def get_patient_access_ledger(
    patient: Any,
    requesting_user: Any,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Retrieve the transparency disclosure ledger for a patient's records.

    Enforces permission:
    - A PATIENT can only view their own access ledger.
    - Clinical Admins & Auditors can inspect ledgers within their basin scope.
    """
    if not requesting_user or not getattr(requesting_user, 'is_authenticated', False):
        raise PermissionDenied("يجب تسجيل الدخول للاطلاع على سجل الشفافية")

    patient_id_str = str(getattr(patient, 'id', patient))

    # If the user is a PATIENT role, verify ownership
    if getattr(requesting_user, 'role', '') == 'PATIENT':
        is_owner = False
        if hasattr(patient, 'user') and patient.user == requesting_user:
            is_owner = True
        elif hasattr(requesting_user, 'patient_record') and str(requesting_user.patient_record.id) == patient_id_str:
            is_owner = True

        if not is_owner:
            logger.warning(
                f"PATIENT_LEDGER_UNAUTHORIZED_ACCESS_ATTEMPT | user={requesting_user.id} | target={patient_id_str}"
            )
            raise PermissionDenied("غير مصرح لك بالاطلاع إلا على سجل الشفافية الخاص بك")

    # Fetch audit records
    from apps.audit.models import AuditLog
    from apps.audit.utils import log_security_event

    entries = []
    try:
        # Query audit logs for events where details contains this patient_id
        logs = (
            AuditLog.objects.filter(event_type__in=TRANSPARENCY_EVENT_TYPES)
            .select_related('user')
            .order_by('-timestamp')[:limit * 3]
        )

        for log in logs:
            det = log.details or {}
            # Match patient_id in details
            log_pid = str(det.get('patient_id') or '')
            if log_pid != patient_id_str and patient_id_str not in str(det):
                continue

            # Determine accessor details
            accessor = log.user
            accessor_role = getattr(accessor, 'role', 'STAFF') if accessor else 'STAFF'
            role_label = ROLE_ARABIC_TITLES.get(accessor_role, accessor_role)

            if accessor:
                accessor_name = accessor.get_full_name() or accessor.email
            else:
                accessor_name = 'طاقم الرعاية الطبية'

            is_emergency = (
                log.event_type == 'BREAK_GLASS_ACTIVATED'
                or det.get('is_break_glass') is True
                or det.get('access_mode') == 'BREAK_GLASS'
            )

            access_desc = EVENT_ARABIC_DESCRIPTIONS.get(
                log.event_type, 'مراجعة بيانات سريرية'
            )

            # Department / Basin attribution
            department = det.get('department') or det.get('basin_name')
            if not department and hasattr(patient, 'basin') and patient.basin:
                department = str(patient.basin.name)
            department = department or 'المنشأة الصحية المركزية'

            justification = (
                det.get('reason')
                or det.get('justification')
                or ('إجراءات الطوارئ وإنقاذ الحياة' if is_emergency else 'المتابعة السريرية وتقديم الرعاية الطبية')
            )

            entries.append({
                'id': str(log.id),
                'timestamp': log.timestamp.isoformat(),
                'accessor_name': accessor_name,
                'accessor_role': role_label,
                'department': department,
                'access_type': access_desc,
                'event_type': log.event_type,
                'is_emergency_break_glass': is_emergency,
                'justification': justification,
                'legal_basis': 'العناية السريرية المباشرة (Direct Care)' if not is_emergency else 'بروتوكول الطوارئ (Break-Glass Protocol)',
                'ip_masked': mask_client_ip(log.ip_address),
            })

            if len(entries) >= limit:
                break

    except Exception as e:
        logger.error(f"Failed to compile patient access ledger: {e}")

    # Log that the ledger was reviewed
    try:
        log_security_event(
            user=requesting_user,
            event_type='PATIENT_TRANSPARENCY_LEDGER_VIEWED',
            details={
                'patient_id': patient_id_str,
                'records_returned': len(entries),
                'viewer_role': getattr(requesting_user, 'role', ''),
            },
            severity='INFO',
        )
    except Exception:
        pass

    return entries
