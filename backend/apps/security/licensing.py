"""
نظام ترخيص الأجهزة — Device licensing service.

متطلب د. مجد: شاشة القفل لا تُرفع إلا للأجهزة المرخصة، والتحقق يتم عبر
عنوان MAC **و** بصمة الجهاز (أي منهما يحدد الجهاز)، وإدارة التفعيل/إلغاء
التفعيل مرتبطة بتلجرام. هذه الوحدة هي القواعد المشتركة التي تلتزم بها كل
مسارات التحكم (بوت تلجرام، لوحة الإدارة، بوابة check-device) حتى لا تتباعد.

الترخيص مستقل عن الثقة: جهاز موثوق لكن ترخيصه ملغى/منتهي → شاشة القفل
تبقى ظاهرة دون إضافة الجهاز للقائمة السوداء، ويمكن إعادة ترخيصه لاحقاً.
"""
import logging
import secrets
from datetime import timedelta

from django.utils import timezone

from apps.security.models import DeviceLicense, DeviceRegistry

logger = logging.getLogger('security')

# Alphabet without visually ambiguous characters (no 0/O, no 1/I/L) so an
# admin can read the key aloud over the phone to activate a device manually.
_KEY_ALPHABET = '23456789ABCDEFGHJKMNPQRSTUVWXYZ'
_KEY_GROUPS, _KEY_GROUP_LEN = 4, 5


def generate_license_key():
    """مفتاح ترخيص بشري القراءة: SMED-XXXXX-XXXXX-XXXXX-XXXXX."""
    body = '-'.join(
        ''.join(secrets.choice(_KEY_ALPHABET) for _ in range(_KEY_GROUP_LEN))
        for _ in range(_KEY_GROUPS)
    )
    return f'SMED-{body}'


def _unique_key():
    """Collision-safe key minting (retries are astronomically enough)."""
    for _ in range(5):
        key = generate_license_key()
        if not DeviceLicense.objects.filter(license_key=key).exists():
            return key
    raise RuntimeError('تعذر توليد مفتاح ترخيص فريد')


def _expires_at_from_days(days):
    if days is None:
        return None
    try:
        days = max(int(days), 1)
    except (TypeError, ValueError):
        return None
    return timezone.now() + timedelta(days=days)


def issue_license(device, issued_by='system', days=None, notes=''):
    """تفعيل/إصدار ترخيص جهاز. Returns (license, created).

    * جهاز بلا ترخيص → يُصدر مفتاحاً جديداً فوراً.
    * ترخيص موجود (معلّق أو ملغى) → يُعاد تفعيله عبر ``reactivate_existing``
      الذي يدوّر المفتاح إن كان ملغىً: مفتاح ملغى سابق لا يُعاد إصداره
      أبداً حتى لا يُعاد استخدام مفتاح تسرب قديم.
    * ``days`` يحدد مدة الترخيص (مثلاً 30 يوماً)؛ ``None`` يعني دائماً.
    """
    license_obj = DeviceLicense.objects.filter(device=device).first()
    if license_obj is None:
        license_obj = DeviceLicense.objects.create(
            device=device,
            license_key=_unique_key(),
            status=DeviceLicense.Status.ACTIVE,
            issued_by=issued_by,
            activated_at=timezone.now(),
            expires_at=_expires_at_from_days(days),
            notes=(notes or '')[:255],
        )
        _log_license_event(device, 'DEVICE_LICENSE_ISSUED',
                           issued_by=issued_by, lic=license_obj, request=None)
        _notify_owner_licensed(device, license_obj)
        return license_obj, True

    license_obj = reactivate_existing(license_obj, issued_by=issued_by, days=days)
    return license_obj, False


def reactivate_existing(license_obj, issued_by='system', days=None):
    """إعادة تفعيل ترخيص موجود مع تدوير مفتاحه إن كان ملغى."""
    updates = ['status', 'deactivated_at', 'activated_at', 'expires_at', 'issued_by']
    if license_obj.status == DeviceLicense.Status.REVOKED:
        license_obj.license_key = _unique_key()
        updates.append('license_key')
    license_obj.status = DeviceLicense.Status.ACTIVE
    license_obj.deactivated_at = None
    license_obj.activated_at = timezone.now()
    license_obj.expires_at = _expires_at_from_days(days)
    license_obj.issued_by = issued_by
    license_obj.save(update_fields=updates)
    _log_license_event(license_obj.device, 'DEVICE_LICENSE_ACTIVATED',
                       issued_by=issued_by, lic=license_obj, request=None)
    _notify_owner_licensed(license_obj.device, license_obj)
    return license_obj


def deactivate_license(device, via='telegram', request=None, suspend=False, notify_owner=True):
    """إلغاء تفعيل ترخيص جهاز (أو تعليقه مؤقتاً مع ``suspend=True``).

    القاعدة الموحدة لكل مسارات الإلغاء (تلجرام/لوحة الإدارة): سحب الترخيص،
    إنهاء جلسات الجهاز فوراً، تدقيق الحدث، وإبلاغ صاحب الجهاز. الجهاز يبقى
    في السجل غير محظور — شاشة القفل تكفي لمنعه.
    """
    license_obj = DeviceLicense.objects.select_related('device__user').filter(device=device).first()
    if license_obj is None:
        return None

    if license_obj.status == DeviceLicense.Status.REVOKED and not license_obj.is_valid:
        return license_obj  # already revoked — idempotent

    license_obj.status = (
        DeviceLicense.Status.SUSPENDED if suspend else DeviceLicense.Status.REVOKED
    )
    license_obj.deactivated_at = timezone.now()
    license_obj.save(update_fields=['status', 'deactivated_at'])

    # An unlicensed device must not keep an open session: the running
    # browser is locked on its very next API call.
    from apps.security.session_security import SessionManager
    SessionManager.force_logout_user(device.user_id)

    event = 'DEVICE_LICENSE_SUSPENDED' if suspend else 'DEVICE_LICENSE_DEACTIVATED'
    _log_license_event(device, event, issued_by=via, lic=license_obj, request=request)
    if notify_owner:
        _notify_owner_licensed(device, license_obj, revoked=not suspend, suspended=suspend)
    return license_obj


def get_device_license(fingerprint=None, mac_address=None):
    """Find the license of a device identified by بصمة **أو** MAC.

    MAC lookup is the fallback when the fingerprint cannot be matched —
    التحقق عبر الماك ادرس "وشي آخر" (البصمة): أي منهما يكفي لتحديد الجهاز،
    والحكم على الترخيص يتقرر من حالة سجل الجهاز نفسه.
    """
    device = None
    if fingerprint:
        device = DeviceRegistry.objects.filter(device_fingerprint=fingerprint).first()
    if device is None and mac_address:
        device = DeviceRegistry.objects.filter(mac_address=mac_address).first()
    if device is None:
        return None
    return (DeviceLicense.objects.select_related('device__user')
            .filter(device=device).first())


def is_device_licensed(fingerprint=None, mac_address=None):
    """True فقط لجهاز يحمل ترخيصاً فعّالاً غير منتهٍ وغير ملغى."""
    license_obj = get_device_license(fingerprint=fingerprint, mac_address=mac_address)
    return bool(license_obj and license_obj.is_valid)


def ensure_device_license(device, issued_by='system'):
    """Lazy provisioning: جهاز موثوق بلا ترخيص (منذ ما قبل هذه الميزة).

    يضمن التوافق الرجعي: كل الأجهزة الموثوقة سابقاً تحصل على ترخيص فعّال
    تلقائياً عند أول تحقق، ومنذ تلك اللحظة يمكن للإدارة إلغاؤه من تلجرام.
    ترخيص ملغى يبقى ملغى — قرار الإدارة لا يُتجاوز.
    """
    license_obj = DeviceLicense.objects.filter(device=device).first()
    if license_obj is not None:
        return license_obj  # exists (valid, suspended, or revoked) — no auto re-issue
    license_obj, _ = issue_license(device, issued_by=issued_by)
    return license_obj


def _log_license_event(device, event_type, issued_by, lic=None, request=None):
    try:
        from apps.audit.utils import log_security_event
        log_security_event(
            user=device.user,
            event_type=event_type,
            request=request,
            details={
                'device_id': str(device.id),
                'device_fingerprint': device.device_fingerprint,
                'mac_address': device.mac_address,
                'license_key': lic.license_key,
                'license_status': lic.effective_status,
                'expires_at': (
                    lic.expires_at.isoformat() if lic.expires_at else None
                ),
                'via': issued_by,
            },
            severity='WARNING' if ('DEACTIVATED' in event_type or 'SUSPENDED' in event_type) else 'INFO',
        )
    except Exception as e:
        logger.error(f'License audit event {event_type} failed: {e}')


def _notify_owner_licensed(device, lic, revoked=False, suspended=False):
    """In-app heads-up to the device owner, best-effort — إشعار صاحب الجهاز."""
    if revoked or suspended:
        title = 'تم تعليق ترخيص أحد أجهزتك' if suspended else 'تم إلغاء ترخيص أحد أجهزتك'
        message = (
            f'أُلغي ترخيص جهازك ({device.os_info or "جهاز"} — MAC: '
            f'{device.mac_address or "غير متوفر"}) بواسطة الإدارة. '
            f'ستواجه شاشة قفل عند محاولة الدخول. إن لم تكن أنت من طلب ذلك تواصل مع الإدارة.'
        )
        notification_type, priority = 'SECURITY_ALERT', 'HIGH'
    else:
        title = 'تم ترخيص أحد أجهزتك'
        message = (
            f'رُخّص جهازك ({device.os_info or "جهاز"} — MAC: '
            f'{device.mac_address or "غير متوفر"}) ويمكنك تسجيل الدخول منه الآن.'
        )
        notification_type, priority = 'LOGIN_ALERT', 'MEDIUM'
    try:
        from apps.security.views import _notify_user
        _notify_user(
            device.user,
            notification_type=notification_type,
            title=title,
            message=message,
            priority=priority,
            data={'device_id': str(device.id), 'license_key': lic.license_key},
        )
    except Exception as e:
        logger.error(f'License owner notification failed: {e}')
