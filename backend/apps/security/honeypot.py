"""
Canary / Honeypot Patient Deception & Threat Intelligence module.

This module implements decoy (Canary) patient records as early-warning tripwires:
- A canary patient appears as an alluring or high-profile clinical record (e.g. VIP,
  dignitary, or anomalous patient file).
- The canary record is never involved in legitimate healthcare workflows or assigned
  to real medical staff.
- Any attempt to query, view, export, or access a canary patient is an unambiguous
  indicator of an insider threat, curious employee snooping, compromised credentials,
  or an automated scraper enumerating IDs.
- When accessed:
  1. An immediate CRITICAL audit log is registered.
  2. The perpetrator's IP is automatically blacklisted in the WAF cache.
  3. A high-priority Telegram operational alert is dispatched to SecOps.
  4. Administrators are notified.
  5. The request is stealthily intercepted (returning a 404 Not Found to prevent
     revealing that the tripwire was triggered).
"""
import logging
import uuid
from typing import Any, Optional, Set

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import PermissionDenied

logger = logging.getLogger('security')

# Cache key storing set of active canary patient IDs
CANARY_CACHE_KEY = 'security:canary_patients:registry'
CANARY_CACHE_TIMEOUT = 86400 * 30  # 30 days default


class CanaryTrapTriggered(PermissionDenied):
    """Exception raised when a canary/honeypot record tripwire is activated."""
    def __init__(self, message="المريض غير موجود", patient_id=None, ip_address=None):
        super().__init__(message)
        self.patient_id = patient_id
        self.ip_address = ip_address


def register_canary_patient(patient_id: Any, note: str = "") -> bool:
    """Register a patient ID as a Canary/Honeypot trap record."""
    if not patient_id:
        return False
    pid_str = str(patient_id).strip().lower()
    try:
        canary_set: Set[str] = set(cache.get(CANARY_CACHE_KEY) or [])
        canary_set.add(pid_str)
        cache.set(CANARY_CACHE_KEY, list(canary_set), timeout=CANARY_CACHE_TIMEOUT)
        logger.info(f"CANARY_PATIENT_REGISTERED | id={pid_str} | note={note}")
        return True
    except Exception as e:
        logger.error(f"Failed to register canary patient {pid_str}: {e}")
        return False


def unregister_canary_patient(patient_id: Any) -> bool:
    """Remove a patient ID from the Canary registry."""
    if not patient_id:
        return False
    pid_str = str(patient_id).strip().lower()
    try:
        canary_set: Set[str] = set(cache.get(CANARY_CACHE_KEY) or [])
        if pid_str in canary_set:
            canary_set.remove(pid_str)
            cache.set(CANARY_CACHE_KEY, list(canary_set), timeout=CANARY_CACHE_TIMEOUT)
            logger.info(f"CANARY_PATIENT_UNREGISTERED | id={pid_str}")
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to unregister canary patient {pid_str}: {e}")
        return False


def get_canary_patient_ids() -> Set[str]:
    """Retrieve all registered Canary patient IDs from cache and settings."""
    ids: Set[str] = set()
    try:
        cached_ids = cache.get(CANARY_CACHE_KEY) or []
        for cid in cached_ids:
            ids.add(str(cid).strip().lower())
    except Exception as e:
        logger.warning(f"Error fetching canary patients from cache: {e}")

    settings_ids = getattr(settings, 'CANARY_PATIENT_IDS', [])
    for sid in settings_ids:
        ids.add(str(sid).strip().lower())

    return ids


def is_canary_patient(patient_or_id: Any) -> bool:
    """Check if a patient instance or ID is a registered Canary record."""
    if patient_or_id is None:
        return False

    # Check explicit attribute on model instance if present
    if getattr(patient_or_id, 'is_canary', False):
        return True

    # Extract ID
    if hasattr(patient_or_id, 'id'):
        target_id = str(patient_or_id.id).strip().lower()
    elif hasattr(patient_or_id, 'pk'):
        target_id = str(patient_or_id.pk).strip().lower()
    else:
        target_id = str(patient_or_id).strip().lower()

    if target_id in get_canary_patient_ids():
        return True

    # Check for [CANARY] tag in full_name or notes if instance
    if hasattr(patient_or_id, 'full_name'):
        name = str(patient_or_id.full_name or '')
        if '[CANARY]' in name.upper() or '[HONEYPOT]' in name.upper():
            return True

    return False


def handle_canary_access(
    user: Any,
    patient_or_id: Any,
    request: Optional[Any] = None,
    action: str = 'view',
    block_ip: bool = True,
) -> dict:
    """Execute defensive countermeasures when a Canary trap is triggered.

    1. Log critical audit event.
    2. Blacklist IP in WAF cache.
    3. Send real-time Telegram critical alert.
    4. Notify security administrators.
    """
    from apps.audit.utils import log_security_event

    patient_id_str = str(getattr(patient_or_id, 'id', patient_or_id))
    client_ip = None

    if request:
        from apps.core.net import get_client_ip
        client_ip = get_client_ip(request)

    user_label = getattr(user, 'email', str(user)) if user else 'Anonymous'

    details = {
        'canary_patient_id': patient_id_str,
        'action': action,
        'client_ip': client_ip,
        'user': user_label,
        'user_id': str(getattr(user, 'id', '')) if user else None,
        'incident': 'CANARY_HONEYPOT_TRIPWIRE_TRIGGERED',
    }

    # 1. Log to immutable audit chain
    try:
        log_security_event(
            user=user,
            event_type='CANARY_PATIENT_ACCESSED',
            request=request,
            details=details,
            severity='CRITICAL',
        )
    except Exception as e:
        logger.exception(f"Failed to log canary audit event: {e}")

    # 2. Block IP in WAF cache & DB
    ip_blocked = False
    if block_ip and client_ip:
        try:
            waf_key = f'waf_blacklist:{client_ip}'
            cache.set(waf_key, True, timeout=86400)  # 24h WAF block
            ip_blocked = True

            from apps.security.models import BlockedIP
            from django.utils import timezone
            from datetime import timedelta

            BlockedIP.objects.update_or_create(
                ip_address=client_ip,
                defaults={
                    'reason': (
                        f'فخ استدراج أمني: محاولة وصول مشبوهة إلى سجل مريض Canary '
                        f'(ID: {patient_id_str}) بواسطة {user_label}'
                    ),
                    'is_active': True,
                    'expires_at': timezone.now() + timedelta(days=1),
                }
            )
        except Exception as e:
            logger.error(f"Failed to persist BlockedIP for canary trigger: {e}")

    # 3. Real-time Telegram alert
    try:
        from apps.security.telegram_service import send_critical_alert
        send_critical_alert(
            '🚨 إنذار أمني حرج: تفعيل فخ استدراج مريض (Canary Trap)',
            [
                f"<b>المستخدم المشتبه به:</b> {user_label}",
                f"<b>عنوان IP:</b> {client_ip or 'غير متوفر'}",
                f"<b>معرف المريض الاستدراجي:</b> {patient_id_str}",
                f"<b>العملية المستهدفة:</b> {action}",
                f"<b>الإجراء التلقائي:</b> {'تم حظر IP في جدار الحماية (WAF)' if ip_blocked else 'تم تسجيل الحادثة'}",
            ]
        )
    except Exception as e:
        logger.exception(f"Failed to send canary Telegram alert: {e}")

    # 4. In-app admin notifications
    try:
        from apps.notifications.utils import send_notification
        from django.contrib.auth import get_user_model
        User = get_user_model()
        admins = User.objects.filter(role__in=['SUPER_ADMIN', 'AUDITOR'], is_active=True)
        for admin in admins:
            send_notification(
                recipient=admin,
                notification_type='SECURITY_ALERT',
                priority='CRITICAL',
                title='إنذار أمني حرج: تفعيل فخ مريض استدراجي',
                message=(
                    f"حاول المستخدم {user_label} الوصول إلى سجل المريض الاستدراجي "
                    f"({patient_id_str}). تم حظر IP وتوثيق الواقعة فورياً."
                ),
                data=details,
            )
    except Exception as e:
        logger.exception(f"Failed to send in-app canary notification: {e}")

    logger.critical(
        f"CANARY_TRAP_TRIGGERED | user={user_label} | ip={client_ip} | patient={patient_id_str} | action={action}"
    )

    return {
        'status': 'triggered',
        'blocked': ip_blocked,
        'client_ip': client_ip,
        'patient_id': patient_id_str,
    }
