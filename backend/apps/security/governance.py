"""
Dual-Custody / Four-Eyes Principle Governance Module.

Implements strict segregation of duties (Dual Authorization) for irreversible
and high-consequence administrative operations:
- Bulk patient data export (FHIR or mass extraction).
- Hard deletion / purge of clinical records or channels.
- Critical system reconfiguration or security bypass.

Rule: A single administrator CANNOT authorize or execute these operations alone.
A second, distinct administrator must review and sign off before execution is unlocked.
"""
import base64
import hmac
import hashlib
import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.utils import timezone

logger = logging.getLogger('security')

FOUR_EYES_CACHE_PREFIX = 'four_eyes:request'
FOUR_EYES_PENDING_KEY = 'four_eyes:pending_ids'
DEFAULT_EXPIRY_SECONDS = 86400  # 24 hours

AUTHORIZED_ADMIN_ROLES = ('SUPER_ADMIN', 'HOSPITAL_ADMIN')


class OperationType:
    BULK_PATIENT_EXPORT = 'BULK_PATIENT_EXPORT'
    RECORD_PURGE = 'RECORD_PURGE'
    SYSTEM_OVERRIDE = 'SYSTEM_OVERRIDE'
    MASS_DELETION = 'MASS_DELETION'

    CHOICES = [
        (BULK_PATIENT_EXPORT, 'تصدير جماعي لبيانات المرضى'),
        (RECORD_PURGE, 'حذف نهائي لسجلات طبية'),
        (SYSTEM_OVERRIDE, 'تجاوز أو تعديل إعدادات أمنية حرجة'),
        (MASS_DELETION, 'حذف جماعي للبيانات أو القنوات'),
    ]


class ApprovalStatus:
    PENDING = 'PENDING'
    APPROVED = 'APPROVED'
    REJECTED = 'REJECTED'
    EXPIRED = 'EXPIRED'
    EXECUTED = 'EXECUTED'


class DualCustodyException(PermissionDenied):
    """Base exception for Dual-Custody / Four-Eyes violations."""
    pass


class DualCustodySelfApprovalForbidden(DualCustodyException):
    """Raised when an administrator attempts to approve their own request."""
    def __init__(self, message="لا يجوز لمقدم الطلب الموافقة على طلبه بنفسه وفق مبدأ الرقابة الثنائية (Four-Eyes Principle)"):
        super().__init__(message)


def _token_payload(request_id: str, approver_id: Any,
                   operation_type: str, target_resource: str) -> str:
    """Canonical, delimiter-safe encoding of everything the token binds.

    Delimited strings do not work here: ``BULK_PATIENT_EXPORT`` contains ``_``
    and ``Patients:All`` contains ``:``, so any choice of separator collides
    with a value and makes the token unparseable (or worse, ambiguous). JSON
    carries arbitrary values, and standard base64 emits no underscore, so the
    ``4EYES_<payload>_<sig>`` shape stays unambiguous.
    """
    body = json.dumps({
        'request_id': str(request_id),
        'approver_id': str(approver_id),
        'operation_type': str(operation_type),
        'target_resource': str(target_resource),
        'issued_at': int(time.time()),
    }, sort_keys=True, separators=(',', ':'))
    return base64.b64encode(body.encode('utf-8')).decode('ascii')


def _generate_execution_token(request_id: str, approver_id: Any,
                              operation_type: str = '', target_resource: str = '') -> str:
    """Generate tamper-proof HMAC authorization token for approved execution.

    The operation type and target are part of the signed payload, so a token
    minted for a RECORD_PURGE cannot be replayed against a BULK_PATIENT_EXPORT:
    the operation the token authorises is bound into the signature, not read
    back from a cache row that can expire or be flushed.
    """
    secret = getattr(settings, 'SECRET_KEY', 'governance-secret-token')
    encoded = _token_payload(request_id, approver_id, operation_type, target_resource)
    sig = hmac.new(
        secret.encode('utf-8'),
        (encoded + '|' + str(int(time.time()))).encode('utf-8'),
        hashlib.sha256
    ).hexdigest()[:32]
    return f"4EYES_{encoded}_{sig}"


def _verify_execution_token_structure(token: str) -> bool:
    """Verify cryptographic signature of execution token."""
    if not token or not token.startswith("4EYES_"):
        return False
    rest = token[len("4EYES_"):]
    # Standard base64 and hex never contain '_', so this split is unambiguous.
    parts = rest.split("_")
    if len(parts) != 2:
        return False
    encoded, provided_sig = parts
    secret = getattr(settings, 'SECRET_KEY', 'governance-secret-token')
    # The signature must cover the payload it accompanies. issued_at is inside
    # the payload, so recompute the same way the generator did.
    try:
        body = json.loads(base64.b64decode(encoded).decode('utf-8'))
        issued = str(body.get('issued_at', ''))
    except Exception:
        return False
    expected_sig = hmac.new(
        secret.encode('utf-8'),
        (encoded + '|' + issued).encode('utf-8'),
        hashlib.sha256
    ).hexdigest()[:32]
    return hmac.compare_digest(provided_sig, expected_sig)


def _parse_execution_token(token: str) -> dict:
    """Extract the bound fields from a verified token.

    Raises DualCustodyException if the token's shape is not what the generator
    produces, so callers never act on an unparseable authorisation.
    """
    try:
        rest = token[len("4EYES_"):]
        encoded = rest.split("_", 1)[0]
        body = json.loads(base64.b64decode(encoded).decode('utf-8'))
        return body
    except Exception:
        raise DualCustodyException("تنسيق رمز التفويض غير صحيح")


def create_approval_request(
    requester: Any,
    operation_type: str,
    target_resource: str,
    payload: Optional[Dict[str, Any]] = None,
    justification: str = "",
    ttl_seconds: int = DEFAULT_EXPIRY_SECONDS,
) -> Dict[str, Any]:
    """Create a pending Dual-Custody authorization request."""
    if not requester or not getattr(requester, 'is_authenticated', False):
        raise PermissionDenied("يجب تسجيل الدخول لتقديم طلب موافقة ثنائية")

    requester_role = getattr(requester, 'role', '')
    if requester_role not in AUTHORIZED_ADMIN_ROLES:
        raise PermissionDenied("وحدهم المسؤولون التنفيذيون مخولون بطلب العمليات الحساسة")

    req_id = str(uuid.uuid4())
    now = timezone.now()
    expires_at = time.time() + ttl_seconds

    # The database row is the authoritative record — the cache is only a fast
    # lookup layered above it. An approval for an irreversible operation must
    # survive a cache flush.
    from apps.security.models import DualCustodyApproval
    approval = DualCustodyApproval.objects.create(
        id=req_id,
        requester=requester,
        operation_type=operation_type,
        target_resource=target_resource,
        payload=payload or {},
        justification=justification,
        status=DualCustodyApproval.Status.PENDING,
        expires_at=timezone.now() + timezone.timedelta(seconds=ttl_seconds),
    )

    request_data = {
        'id': req_id,
        'operation_type': operation_type,
        'target_resource': target_resource,
        'payload': payload or {},
        'justification': justification,
        'status': ApprovalStatus.PENDING,
        'requester_id': str(getattr(requester, 'id', requester.pk)),
        'requester_email': getattr(requester, 'email', str(requester)),
        'requester_role': requester_role,
        'created_at': now.isoformat(),
        'expires_at_timestamp': expires_at,
        'approver_id': None,
        'approver_email': None,
        'reviewed_at': None,
        'execution_token': None,
        'review_notes': '',
    }

    # Mirror into cache for the fast paths (listing, verification).
    cache_key = f"{FOUR_EYES_CACHE_PREFIX}:{req_id}"
    cache.set(cache_key, request_data, timeout=ttl_seconds)

    # Track in pending set
    pending_ids = set(cache.get(FOUR_EYES_PENDING_KEY) or [])
    pending_ids.add(req_id)
    cache.set(FOUR_EYES_PENDING_KEY, list(pending_ids), timeout=DEFAULT_EXPIRY_SECONDS * 7)

    # Log to audit trail
    try:
        from apps.audit.utils import log_security_event
        log_security_event(
            user=requester,
            event_type='FOUR_EYES_REQUEST_CREATED',
            details={
                'request_id': req_id,
                'operation_type': operation_type,
                'target_resource': target_resource,
                'justification': justification,
            },
            severity='WARNING',
        )
    except Exception as e:
        logger.error(f"Failed to log FOUR_EYES_REQUEST_CREATED: {e}")

    # Dispatch SecOps Telegram notification
    try:
        from apps.security.telegram_service import send_critical_alert
        send_critical_alert(
            'طلب موافقة ثنائية مطلوب (Four-Eyes Approval Required)',
            [
                f"<b>نوع العملية:</b> {operation_type}",
                f"<b>مقدم الطلب:</b> {request_data['requester_email']} ({requester_role})",
                f"<b>المورد المستهدف:</b> {target_resource}",
                f"<b>التبرير:</b> {justification or 'لم يُذكر'}",
                f"<b>معرف الطلب:</b> <code>{req_id}</code>",
                "<b>الإجراء المطلوب:</b> يتطلب التنفيذ مراجعة وتوقيع مسؤول ثانٍ مستقل",
            ]
        )
    except Exception as e:
        logger.error(f"Failed to send Four-Eyes Telegram alert: {e}")

    return request_data


def _load_approval_from_db(request_id: str) -> Optional[Dict[str, Any]]:
    """Rebuild the request dict from the authoritative database row.

    Used on a cache miss or after a cache flush, so an approval for an
    irreversible operation does not vanish because Redis was cleared.
    """
    from apps.security.models import DualCustodyApproval
    try:
        a = DualCustodyApproval.objects.get(pk=request_id)
    except DualCustodyApproval.DoesNotExist:
        return None
    except Exception as e:
        logger.error(f"Failed to load dual-custody approval {request_id}: {e}")
        return None

    return {
        'id': str(a.id),
        'operation_type': a.operation_type,
        'target_resource': a.target_resource,
        'payload': a.payload or {},
        'justification': a.justification,
        'status': a.status,
        'requester_id': str(a.requester_id),
        'requester_email': getattr(a.requester, 'email', ''),
        'requester_role': getattr(a.requester, 'role', ''),
        'created_at': a.requested_at.isoformat() if a.requested_at else None,
        # Wall-clock expiry for the token TTL math below.
        'expires_at_timestamp': a.expires_at.timestamp() if a.expires_at else 0,
        'approver_id': str(a.approver_id) if a.approver_id else None,
        'approver_email': getattr(a.approver, 'email', None) if a.approver_id else None,
        'reviewed_at': a.reviewed_at.isoformat() if a.reviewed_at else None,
        'execution_token': None,
        'review_notes': a.review_notes or '',
    }


def _sync_approval_status(request_id: str, status: str, **fields) -> None:
    """Mirror a status change into the authoritative database row."""
    try:
        from apps.security.models import DualCustodyApproval
        updates = {'status': status}
        updates.update(fields)
        DualCustodyApproval.objects.filter(pk=request_id).update(**updates)
    except Exception as e:
        logger.error(f"Failed to sync dual-custody status {request_id}: {e}")


def approve_request(approver: Any, request_id: str, notes: str = "") -> Dict[str, Any]:
    """Approve a Dual-Custody request by a SECOND independent administrator."""
    if not approver or not getattr(approver, 'is_authenticated', False):
        raise PermissionDenied("المصادقة مطلوبة للاعتماد")

    approver_role = getattr(approver, 'role', '')
    if approver_role not in AUTHORIZED_ADMIN_ROLES:
        raise PermissionDenied("الصلاحية غير كافية لاعتماد الطلب")

    cache_key = f"{FOUR_EYES_CACHE_PREFIX}:{request_id}"
    req_data = cache.get(cache_key)
    if not req_data:
        # Cache miss or flush: the database row is the authoritative record.
        req_data = _load_approval_from_db(request_id)
    if not req_data:
        raise DualCustodyException("طلب الموافقة غير موجود أو انتهت صلاحيته")

    # Verify not expired
    if time.time() > req_data.get('expires_at_timestamp', 0):
        req_data['status'] = ApprovalStatus.EXPIRED
        cache.set(cache_key, req_data, timeout=3600)
        _sync_approval_status(request_id, ApprovalStatus.EXPIRED)
        raise DualCustodyException("انتهت صلاحية طلب الموافقة")

    if req_data.get('status') != ApprovalStatus.PENDING:
        raise DualCustodyException(f"لا يمكن اعتماد طلب بحالة: {req_data.get('status')}")

    # ENFORCE FOUR-EYES PRINCIPLE: Approver CANNOT be the Requester!
    approver_id = str(getattr(approver, 'id', approver.pk))
    if approver_id == req_data.get('requester_id'):
        logger.warning(
            f"FOUR_EYES_SELF_APPROVAL_ATTEMPT_BLOCKED | user={approver_id} | req={request_id}"
        )
        raise DualCustodySelfApprovalForbidden()

    # Generate one-time execution token. The operation type and target are
    # bound into the signature so the token cannot be replayed against a
    # different operation.
    token = _generate_execution_token(
        request_id, approver_id,
        operation_type=req_data.get('operation_type', ''),
        target_resource=req_data.get('target_resource', ''),
    )

    now_dt = timezone.now()
    now = now_dt.isoformat()
    req_data['status'] = ApprovalStatus.APPROVED
    req_data['approver_id'] = approver_id
    req_data['approver_email'] = getattr(approver, 'email', str(approver))
    req_data['reviewed_at'] = now
    req_data['review_notes'] = notes
    req_data['execution_token'] = token

    # Persist the approval and the token to the database — this is what
    # survives a cache flush.
    from apps.security.models import DualCustodyApproval
    DualCustodyApproval.objects.filter(pk=request_id).update(
        status=DualCustodyApproval.Status.APPROVED,
        approver=approver,
        reviewed_at=now_dt,
        review_notes=notes,
    )

    # Save approved state (remaining TTL)
    ttl = max(60, int(req_data.get('expires_at_timestamp', 0) - time.time()))
    cache.set(cache_key, req_data, timeout=ttl)

    # Remove from pending list
    pending_ids = set(cache.get(FOUR_EYES_PENDING_KEY) or [])
    if request_id in pending_ids:
        pending_ids.remove(request_id)
        cache.set(FOUR_EYES_PENDING_KEY, list(pending_ids), timeout=DEFAULT_EXPIRY_SECONDS * 7)

    # Log to audit trail
    try:
        from apps.audit.utils import log_security_event
        log_security_event(
            user=approver,
            event_type='FOUR_EYES_REQUEST_APPROVED',
            details={
                'request_id': request_id,
                'operation_type': req_data['operation_type'],
                'requester_id': req_data['requester_id'],
                'notes': notes,
            },
            severity='CRITICAL',
        )
    except Exception as e:
        logger.error(f"Failed to log FOUR_EYES_REQUEST_APPROVED: {e}")

    return req_data


def reject_request(reviewer: Any, request_id: str, rejection_reason: str = "") -> Dict[str, Any]:
    """Reject a Dual-Custody request."""
    if not reviewer or not getattr(reviewer, 'is_authenticated', False):
        raise PermissionDenied("المصادقة مطلوبة لرفض الطلب")

    if getattr(reviewer, 'role', '') not in AUTHORIZED_ADMIN_ROLES:
        raise PermissionDenied("الصلاحية غير كافية لمراجعة الطلب")

    cache_key = f"{FOUR_EYES_CACHE_PREFIX}:{request_id}"
    req_data = cache.get(cache_key)
    if not req_data:
        req_data = _load_approval_from_db(request_id)
    if not req_data:
        raise DualCustodyException("طلب الموافقة غير موجود")

    req_data['status'] = ApprovalStatus.REJECTED
    req_data['approver_id'] = str(getattr(reviewer, 'id', reviewer.pk))
    req_data['approver_email'] = getattr(reviewer, 'email', str(reviewer))
    req_data['reviewed_at'] = timezone.now().isoformat()
    req_data['review_notes'] = rejection_reason

    cache.set(cache_key, req_data, timeout=86400)
    _sync_approval_status(
        request_id, ApprovalStatus.REJECTED,
        review_notes=rejection_reason, rejection_reason=rejection_reason,
    )

    pending_ids = set(cache.get(FOUR_EYES_PENDING_KEY) or [])
    if request_id in pending_ids:
        pending_ids.remove(request_id)
        cache.set(FOUR_EYES_PENDING_KEY, list(pending_ids), timeout=DEFAULT_EXPIRY_SECONDS * 7)

    try:
        from apps.audit.utils import log_security_event
        log_security_event(
            user=reviewer,
            event_type='FOUR_EYES_REQUEST_REJECTED',
            details={'request_id': request_id, 'reason': rejection_reason},
            severity='WARNING',
        )
    except Exception:
        pass

    return req_data


def verify_and_consume_token(
    operation_type: str,
    executor: Any,
    execution_token: str,
) -> Dict[str, Any]:
    """Verify execution authorization token and consume it (single-use).

    Raises PermissionDenied / DualCustodyException if invalid.
    """
    if not _verify_execution_token_structure(execution_token):
        raise DualCustodyException("رمز التفويض الثنائي غير صالح تشفيرياً أو متلاعب به")

    # The bound fields come from the token's own signature, not from a lookup.
    try:
        token_fields = _parse_execution_token(execution_token)
    except DualCustodyException:
        raise
    req_id = token_fields['request_id']

    # The operation type the token was minted for must match the one being
    # executed — bound into the HMAC, so it cannot be substituted.
    if token_fields['operation_type'] != operation_type:
        raise DualCustodyException(
            "رمز التفويض لا يطابق نوع العملية المطلوب تنفيذها (النوع مثبَّت في التوقيع)"
        )

    cache_key = f"{FOUR_EYES_CACHE_PREFIX}:{req_id}"
    req_data = cache.get(cache_key)
    if not req_data:
        # Cache flushed or expired — the database row is authoritative.
        req_data = _load_approval_from_db(req_id)
    if not req_data:
        raise DualCustodyException("سجل الموافقة الثنائية غير موجود أو منتهي الصلاحية")

    if req_data.get('status') == ApprovalStatus.EXECUTED:
        raise DualCustodyException("تم استخدام رمز الموافقة الثنائية هذا مسبقاً (Replay Attack Prevented)")

    if req_data.get('status') != ApprovalStatus.APPROVED:
        raise DualCustodyException(f"الطلب غير معتمد (الحالة الحالية: {req_data.get('status')})")

    if req_data.get('operation_type') != operation_type:
        raise DualCustodyException("رمز التفويض لا يطابق نوع العملية المطلوب تنفيذها")

    # Check expiration
    if time.time() > req_data.get('expires_at_timestamp', 0):
        req_data['status'] = ApprovalStatus.EXPIRED
        cache.set(cache_key, req_data, timeout=3600)
        _sync_approval_status(req_id, ApprovalStatus.EXPIRED)
        raise DualCustodyException("انتهت صلاحية رمز التفويض")

    # Mark as EXECUTED (Single-use consume)
    now_dt = timezone.now()
    req_data['status'] = ApprovalStatus.EXECUTED
    req_data['executed_by'] = str(getattr(executor, 'id', getattr(executor, 'pk', 'Anonymous')))
    req_data['executed_at'] = now_dt.isoformat()
    cache.set(cache_key, req_data, timeout=86400)
    # Persisting the executed state is what makes the token single-use across a
    # cache flush: without it, clearing Redis would un-consume the token.
    _sync_approval_status(
        req_id, ApprovalStatus.EXECUTED,
        executed_at=now_dt,
        executed_by=executor if getattr(executor, 'is_authenticated', False) else None,
    )

    try:
        from apps.audit.utils import log_security_event
        log_security_event(
            user=executor,
            event_type='FOUR_EYES_OPERATION_EXECUTED',
            details={
                'request_id': req_id,
                'operation_type': operation_type,
                'approver_id': req_data.get('approver_id'),
                'target_resource': req_data.get('target_resource'),
            },
            severity='CRITICAL',
        )
    except Exception:
        pass

    logger.info(
        f"FOUR_EYES_OPERATION_EXECUTED | type={operation_type} | req={req_id} | executor={executor}"
    )
    return req_data
