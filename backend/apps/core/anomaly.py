"""PHI access velocity anomaly detection.

A clinician reviewing a case reads a handful of files; an insider exfiltrating a
patient index reads hundreds. The audit trail records every read, but it only
answers questions after the fact — someone has to look. This module makes the
"someone" automatic: every PHI file read bumps shared-cache counters, and a
caller whose velocity crosses a threshold is flagged immediately, while the
reading is still happening.

Design notes:

* Counters live in the shared cache (Redis in production, DatabaseCache in the
  no-Redis fallback), so the count is coherent across gunicorn workers — the
  same reason rate limiting lives there.
* Detection is deliberately non-blocking in effect: nothing here refuses a
  request. A clinician with a legitimate bulk task (a discharge summary pulling
  every scan of a long stay) must not be locked out of care; the point is the
  alert, not the lock. Blocking is the WAF's job, with its own review path.
* The alert itself is throttled per user, or an automated scan that reads
  continuously would produce one audit row and one Telegram message per file.
"""
import logging

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger('security')

# Sliding-window buckets, as (cache-suffix, window_seconds, threshold).
# 40 distinct files in 5 minutes, or 120 in an hour, is far above any real
# clinical review pattern and far below an exfiltration rate — both windows must
# be crossed before anything fires, which keeps a burst of legitimate opens
# during one busy minute from paging anyone.
_WINDOWS = (
    ('5m', 300, 40),
    ('1h', 3600, 120),
)

_ALERT_COOLDOWN_SECONDS = 600
_CACHE_PREFIX = 'phi-velocity'

# EHR Hopping detection windows:
# An insider browsing > 15 distinct patients in 5 minutes, or > 40 in 1 hour,
# represents abnormal chart snooping / exfiltration behavior.
_HOPPING_WINDOWS = (
    ('5m', 300, 15),
    ('1h', 3600, 40),
)
_HOPPING_CACHE_PREFIX = 'ehr-hopping'


def _threshold_scale():
    """Operator override for the built-in thresholds.

    Radiology-heavy deployments legitimately read more images than the default
    assumes. A scalar (0.5 doubles every threshold, 2 halves them) is enough to
    tune the dial without this module growing a settings schema.
    """
    try:
        scale = float(getattr(settings, 'PHI_ANOMALY_THRESHOLD_SCALE', 1.0))
    except (TypeError, ValueError):
        return 1.0
    return max(scale, 0.01)


def record_phi_access(user, resource='file', path=''):
    """Record one PHI read and return True when the user crosses a threshold.

    Returns False for anonymous callers (nothing to attribute) and for every
    read under threshold. The return value is informational — callers do not
    need to branch on it; the alerting side effect is the feature.
    """
    if user is None or not getattr(user, 'is_authenticated', False):
        return False

    scale = _threshold_scale()
    crossed = None
    per_user = {}

    for suffix, window, threshold in _WINDOWS:
        key = f'{_CACHE_PREFIX}:{user.id}:{suffix}'
        count = (cache.get(key) or 0) + 1
        # add() only sets when absent, so the TTL restarts once per window;
        # subsequent increments within the window keep the original expiry.
        cache.add(key, count, timeout=window)
        cache.set(key, count, timeout=window)
        per_user[suffix] = count
        if count > threshold * scale and crossed is None:
            crossed = {
                'window': suffix,
                'count': count,
                'threshold': int(threshold * scale),
            }

    if crossed:
        _raise_anomaly(user, resource, path, crossed, per_user)
        return True
    return False


def _raise_anomaly(user, resource, path, crossed, per_user):
    """Flag the velocity breach once per cooldown, then stay quiet.

    The audit row and the Telegram alert are both throttled: an ongoing bulk
    read still surfaces on the next cooldown tick, which is enough to catch it
    while remaining quiet enough that a human actually reads the chat.
    """
    from apps.audit.utils import log_security_event

    cool_key = f'{_CACHE_PREFIX}:alerted:{user.id}'
    is_first_alert = not cache.get(cool_key)
    cache.set(cool_key, 1, timeout=_ALERT_COOLDOWN_SECONDS)

    details = {
        'resource': resource,
        'path': path[:255],
        'velocity': per_user,
        'crossed': crossed,
        'threshold_scale': _threshold_scale(),
    }
    log_security_event(
        user=user,
        event_type='SUSPICIOUS_ACTIVITY',
        severity='WARNING',
        details=details,
    )

    if not is_first_alert:
        return

    logger.warning(
        'PHI access anomaly: user=%s velocity=%s',
        getattr(user, 'email', user.pk),
        per_user,
    )
    try:
        from apps.security.telegram_service import send_critical_alert
        send_critical_alert(
            'نشاط وصول مشبوه للملفات الطبية',
            [
                f"<b>المستخدم:</b> {getattr(user, 'email', user.pk)}",
                f"<b>العدد:</b> {crossed['count']} ملف خلال {crossed['window']}",
                f"<b>الحد المسموح:</b> {crossed['threshold']}",
                f"<b>المورد:</b> {resource}",
            ],
        )
    except Exception:  # never let alerting break the request thread
        logger.exception('Failed to deliver PHI anomaly alert')

    try:
        from apps.notifications.utils import send_notification
        admins = None
        from django.contrib.auth import get_user_model
        User = get_user_model()
        admins = User.objects.filter(
            role__in=['SUPER_ADMIN', 'AUDITOR'], is_active=True
        )
        for admin in admins:
            send_notification(
                recipient=admin,
                notification_type='SECURITY_ALERT',
                priority='HIGH',
                title='نشاط وصول مشبوه للملفات الطبية',
                message=(
                    f"المستخدم {getattr(user, 'email', user.pk)} تجاوز معدل الوصول "
                    f"للملفات الطبية ({crossed['count']} خلال {crossed['window']}). "
                    f"راجع سجل التدقيق للتفاصيل."
                ),
                data=details,
            )
    except Exception:
        logger.exception('Failed to notify admins of PHI anomaly')


def record_patient_hopping(user, patient_id):
    """Track distinct patient charts viewed by a user to detect EHR hopping.

    EHR Hopping occurs when an insider, curious clinician, or compromised account
    browses through dozens of unrelated patient records (e.g. snooping on VIPs or
    harvesting hospital registries).

    Returns True if an anomaly threshold was crossed, False otherwise.
    """
    if user is None or not getattr(user, 'is_authenticated', False):
        return False
    if not patient_id:
        return False

    patient_str = str(patient_id).strip().lower()
    scale = _threshold_scale()
    crossed = None
    per_window_counts = {}

    for suffix, window, threshold in _HOPPING_WINDOWS:
        key = f'{_HOPPING_CACHE_PREFIX}:{user.id}:{suffix}'
        current_set = cache.get(key)
        if current_set is None:
            current_set = set()
        elif isinstance(current_set, (list, tuple)):
            current_set = set(current_set)

        if patient_str not in current_set:
            current_set.add(patient_str)
            cache.set(key, current_set, timeout=window)

        count = len(current_set)
        per_window_counts[suffix] = count

        effective_threshold = int(threshold * scale)
        if count > effective_threshold and crossed is None:
            crossed = {
                'window': suffix,
                'count': count,
                'threshold': effective_threshold,
            }

    if crossed:
        _raise_hopping_anomaly(user, patient_str, crossed, per_window_counts)
        return True
    return False


def _raise_hopping_anomaly(user, last_patient_id, crossed, per_window_counts):
    """Flag EHR hopping breach once per cooldown window, then stay quiet."""
    from apps.audit.utils import log_security_event

    cool_key = f'{_HOPPING_CACHE_PREFIX}:alerted:{user.id}'
    is_first_alert = not cache.get(cool_key)
    cache.set(cool_key, 1, timeout=_ALERT_COOLDOWN_SECONDS)

    details = {
        'last_patient_id': last_patient_id,
        'hopping_counts': per_window_counts,
        'crossed': crossed,
        'threshold_scale': _threshold_scale(),
        'detection_type': 'EHR_HOPPING_ANOMALY',
    }
    log_security_event(
        user=user,
        event_type='EHR_HOPPING_ANOMALY',
        severity='WARNING',
        details=details,
    )

    if not is_first_alert:
        return

    logger.warning(
        'EHR hopping anomaly detected: user=%s counts=%s',
        getattr(user, 'email', user.pk),
        per_window_counts,
    )
    try:
        from apps.security.telegram_service import send_critical_alert
        send_critical_alert(
            'سلوك سريري مشبوه: تنقل مفرط بين سجلات المرضى (EHR Hopping)',
            [
                f"<b>المستخدم:</b> {getattr(user, 'email', user.pk)}",
                f"<b>العدد:</b> {crossed['count']} مريض مختلف خلال {crossed['window']}",
                f"<b>الحد المسموح:</b> {crossed['threshold']} مريض",
                f"<b>آخر مريض تم الوصول له:</b> {last_patient_id}",
            ],
        )
    except Exception:
        logger.exception('Failed to deliver EHR hopping alert')

    try:
        from apps.notifications.utils import send_notification
        from django.contrib.auth import get_user_model
        User = get_user_model()
        admins = User.objects.filter(
            role__in=['SUPER_ADMIN', 'AUDITOR'], is_active=True
        )
        for admin in admins:
            send_notification(
                recipient=admin,
                notification_type='SECURITY_ALERT',
                priority='HIGH',
                title='تنبيه أمني: تنقل مفرط بين ملفات المرضى',
                message=(
                    f"المستخدم {getattr(user, 'email', user.pk)} قام بفتح "
                    f"{crossed['count']} ملف مريض مختلف خلال {crossed['window']}. "
                    f"يرجى مراجعة سجل التدقيق."
                ),
                data=details,
            )
    except Exception:
        logger.exception('Failed to notify admins of EHR hopping')

