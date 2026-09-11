"""
Telegram admin console — control the platform from the chat itself.

د. مجد's requirement was activation control over Telegram; this generalizes
it into a command surface so the admin never needs the dashboard open:

    /pending              الأجهزة بانتظار الموافقة
    /approve <id>         تفعيل جهاز (+ إصدار ترخيص)
    /block <id>           حظر جهاز (سحب ثقة + قائمة سوداء + قتل جلسة)
    /unblock <fp-prefix>  رفع حظر عن جهاز
    /devices [n]          آخر الأجهزة المسجلة
    /licenses [n]         تراخيص الأجهزة وحالتها
    /license <id> [أيام]  ترخيص/تجديد ترخيص جهاز (بدون أيام = دائم)
    /revoke <id>          إلغاء ترخيص جهاز (شاشة القفل تظل ظاهرة)
    /users [بحث]          المستخدمون (بريد، دور، حالة)
    /stats                إحصاءات المنصة
    /backups [n]          آخر النسخ الاحتياطية وحالة تسليمها
    /backup [FULL|DATABASE|MEDIA]   إنشاء نسخة الآن

Two delivery paths share one processor (process_update):
* TelegramWebhookView — production, Telegram pushes updates to a public URL;
* the `telegram_bot` management command — long-polling getUpdates, which is
  how a localhost deployment receives commands without ngrok.

Authorization: only TELEGRAM_ADMIN_CHAT_ID may issue commands. A stranger
texting the bot gets a fixed refusal with no platform details.
"""
import logging

from django.conf import settings
from django.utils import timezone

from apps.accounts.models import User
from apps.backups.models import BackupRecord
from apps.patients.models import Patient
from apps.security.models import BlockedDevice, DeviceRegistry

logger = logging.getLogger('security')

MAX_LIST = 10

HELP_TEXT = (
    "🛡 <b>SecureMed — وحدة تحكم الإدارة</b>\n\n"
    "<b>الأجهزة والترخيص</b>\n"
    "/pending — الأجهزة بانتظار الموافقة\n"
    "/approve &lt;id&gt; — تفعيل جهاز (+ إصدار ترخيص)\n"
    "/block &lt;id&gt; — حظر جهاز (سحب ثقة + قائمة سوداء + إنهاء جلسة)\n"
    "/unblock &lt;بصمة&gt; — رفع حظر عن جهاز\n"
    "/devices [عدد] — آخر الأجهزة المسجلة\n"
    "/licenses [عدد] — تراخيص الأجهزة\n"
    "/license &lt;id&gt; [أيام] — ترخيص/تجديد جهاز (بدون أيام = دائم)\n"
    "/revoke &lt;id&gt; — إلغاء ترخيص جهاز\n\n"
    "<b>المستخدمون والمنصة</b>\n"
    "/users [بحث] — المستخدمون\n"
    "/stats — إحصاءات المنصة\n\n"
    "<b>النسخ الاحتياطي</b>\n"
    "/backups [عدد] — آخر النسخ وحالة تسليمها\n"
    "/backup [FULL|DATABASE|MEDIA] — إنشاء نسخة الآن\n\n"
    "<i>كل الأوامر مقصورة على شات الإدارة.</i>"
)

UNAUTHORIZED_TEXT = "⛔ هذا البوت مخصص لإدارة النظام فقط."


def _is_admin_chat(chat_id):
    admin = str(getattr(settings, 'TELEGRAM_ADMIN_CHAT_ID', ''))
    return admin and str(chat_id) == admin


def _fmt_device(d, with_buttons_hint=False):
    status = '✅ موثوق' if d.is_trusted else '⏳ بانتظار الموافقة'
    blocked = '⛔ محظور' if BlockedDevice.objects.enforceable().filter(
        device_fingerprint=d.device_fingerprint).exists() else ''
    license_label = _license_badge(d)
    state = ' '.join(x for x in (status, blocked, license_label) if x)
    return (
        f"<code>{d.id}</code>\n"
        f"👤 {d.user.email}\n"
        f"🖥 {d.os_info or 'نظام غير معروف'} — IP: {d.last_ip_address or '؟'}\n"
        f"🔑 MAC: <code>{d.mac_address or 'غير متوفر'}</code>\n"
        f"الحالة: {state}\n"
        f"🕒 {timezone.localtime(d.last_login).strftime('%m-%d %H:%M')}"
    )


_LICENSE_BADGES = {
    'ACTIVE': '🪪 مرخص',
    'SUSPENDED': '⏸ ترخيص معلق',
    'REVOKED': '🚫 ترخيص ملغى',
    'EXPIRED': '⌛ ترخيص منتهي',
    'MISSING': '❔ بلا ترخيص',
}


def _license_badge(device):
    """ترخيص الجهاز كما يظهر في قوائم البوت — بلا استعلام إضافي إن أمكن."""
    if hasattr(device, 'license'):
        lic = device.license  # select_related ready when the caller prefetches
    else:
        from apps.security.models import DeviceLicense
        lic = DeviceLicense.objects.filter(device=device).first()
    if lic is None:
        return _LICENSE_BADGES['MISSING']
    return _LICENSE_BADGES.get(lic.effective_status, lic.effective_status)


def _cmd_pending():
    pending = list(
        DeviceRegistry.objects.filter(is_trusted=False)
        .select_related('user').order_by('-last_login')
    )
    if not pending:
        return "✅ لا توجد أجهزة بانتظار الموافقة."
    lines = [f"⏳ <b>بانتظار الموافقة ({len(pending)}):</b>\n"]
    lines += [_fmt_device(d) for d in pending[:MAX_LIST]]
    if len(pending) > MAX_LIST:
        lines.append(f"\nو{len(pending) - MAX_LIST} أخرى…")
    lines.append("\nللموافقة: <code>/approve &lt;المعرف&gt;</code>")
    return "\n".join(lines)


def _find_device(ref):
    """Resolve a device by UUID id or fingerprint prefix."""
    device = DeviceRegistry.objects.filter(id=str(ref)).first()
    if device:
        return device
    return DeviceRegistry.objects.filter(
        device_fingerprint__startswith=str(ref)[:32],
    ).select_related('user').first()


def _cmd_approve(ref):
    device = _find_device(ref)
    if device is None:
        return f"❌ لم أجد جهازاً بالمعرف/البصمة: <code>{ref}</code>"
    if device.is_trusted:
        return "ℹ️ الجهاز موثوق بالفعل."
    device.is_trusted = True
    device.save(update_fields=['is_trusted'])
    # تفعيل الجهاز يعني ترخيصه: الموافقة تُصدر الترخيص تلقائياً فيرفع
    # شاشة القفل عن الجهاز فوراً.
    from apps.security.licensing import issue_license
    license_obj, _created = issue_license(device, issued_by='telegram-command')
    from apps.security.views import log_security_event
    log_security_event(
        user=device.user,
        event_type='DEVICE_TRUSTED',
        request=None,
        details={'device_id': str(device.id),
                 'device_fingerprint': device.device_fingerprint,
                 'granted_by': 'telegram-command'},
    )
    from apps.notifications.utils import send_notification
    send_notification(
        recipient=device.user,
        notification_type='LOGIN_ALERT',
        title='تم تفعيل جهاز جديد',
        message=(
            f'تمت الموافقة على جهازك ({device.os_info or "جهاز"} — '
            f'بصمة: {device.device_fingerprint[:16]}…) عبر بوت الإدارة، '
            f'ويمكنك تسجيل الدخول منه الآن.'
        ),
        priority='MEDIUM',
        data={'device_id': str(device.id)},
    )
    return (
        f"✅ تم تفعيل وترخيص جهاز <b>{device.user.email}</b>\n"
        f"<code>{device.device_fingerprint[:32]}</code>\n"
        f"🪪 مفتاح الترخيص: <code>{license_obj.license_key}</code>"
    )


def _cmd_block(ref):
    device = _find_device(ref)
    if device is None:
        return f"❌ لم أجد جهازاً بالمعرف/البصمة: <code>{ref}</code>"
    from apps.security.views import _deactivate_device
    _deactivate_device(device, request=None, via='telegram-command', block=True)
    return (
        f"🔒 تم حظر جهاز <b>{device.user.email}</b>\n"
        f"<code>{device.device_fingerprint[:32]}</code>\n"
        "سُحبت الثقة، أُضيف للقائمة السوداء، وانتهت جلساته."
    )


def _cmd_unblock(fp_prefix):
    blocked = BlockedDevice.objects.enforceable().filter(
        device_fingerprint__startswith=str(fp_prefix)[:32],
    ).first()
    if blocked is None:
        return f"❌ لا يوجد حظر نشط يطابق: <code>{fp_prefix}</code>"
    blocked.is_active = False
    blocked.save(update_fields=['is_active'])
    from django.core.cache import cache
    cache.delete(f'waf_device_blacklist:{blocked.device_fingerprint}')
    cache.delete(
        f'blocked_device:{blocked.device_fingerprint}:{blocked.mac_address or ""}'
    )
    return (
        f"🔓 رُفع الحظر عن <code>{blocked.device_fingerprint[:32]}</code>\n"
        "سيُقبل الجهاز من الطلب التالي — تفعيله يتطلب /approve."
    )


def _cmd_devices(limit):
    devices = DeviceRegistry.objects.select_related('user', 'license').order_by(
        '-last_login'
    )[:min(max(limit, 1), MAX_LIST)]
    if not devices:
        return "لا توجد أجهزة مسجلة."
    lines = [f"🖥 <b>آخر الأجهزة ({devices.count()}):</b>\n"]
    lines += [_fmt_device(d) for d in devices]
    return "\n".join(lines)


def _cmd_licenses(limit):
    from apps.security.models import DeviceLicense
    licenses = DeviceLicense.objects.select_related(
        'device__user',
    ).order_by('-issued_at')[:min(max(limit, 1), MAX_LIST)]
    if not licenses:
        return "لا توجد تراخيص بعد. ترخيص جهاز: /license &lt;id&gt;"
    lines = [f"🪪 <b>تراخيص الأجهزة:</b>\n"]
    for lic in licenses:
        d = lic.device
        lines.append(
            f"• <code>{lic.license_key}</code>\n"
            f"  👤 {d.user.email} — MAC: <code>{d.mac_address or '؟'}</code>\n"
            f"  الحالة: {_LICENSE_BADGES.get(lic.effective_status, lic.effective_status)}"
            + (
                f" — ينتهي: {timezone.localtime(lic.expires_at).strftime('%m-%d %H:%M')}"
                if lic.expires_at else ' — دائم'
            )
        )
    return "\n".join(lines)


def _cmd_license(ref, days=None):
    """ترخيص/تجديد جهاز: /license <id> [أيام] — الإلغاء عبر /revoke."""
    from apps.security.licensing import issue_license
    device = _find_device(ref)
    if device is None:
        return f"❌ لم أجد جهازاً بالمعرف/البصمة: <code>{ref}</code>"
    license_obj, created = issue_license(device, issued_by='telegram-command', days=days)
    expiry = (
        f'ينتهي في {timezone.localtime(license_obj.expires_at).strftime("%m-%d %H:%M")}'
        if license_obj.expires_at else 'دائم'
    )
    action = 'أُصدر ترخيص جديد' if created else 'جُدّد التفعيل'
    return (
        f"🪪 {action} لجهاز <b>{device.user.email}</b>\n"
        f"<code>{device.device_fingerprint[:32]}</code>\n"
        f"المفتاح: <code>{license_obj.license_key}</code>\n"
        f"المدة: {expiry}"
    )


def _cmd_revoke(ref):
    """إلغاء ترخيص جهاز: شاشة القفل تظل ظاهرة دون قائمة سوداء."""
    from apps.security.licensing import deactivate_license
    from apps.security.models import DeviceLicense
    device = _find_device(ref)
    if device is None:
        return f"❌ لم أجد جهازاً بالمعرف/البصمة: <code>{ref}</code>"
    if not DeviceLicense.objects.filter(device=device).exists():
        return "ℹ️ هذا الجهاز لا يحمل ترخيصاً أصلاً."
    if DeviceLicense.objects.filter(
        device=device, status=DeviceLicense.Status.REVOKED,
    ).exists():
        return "ℹ️ ترخيص هذا الجهاز ملغى بالفعل."
    deactivate_license(device, via='telegram-command')
    return (
        f"🚫 أُلغي ترخيص جهاز <b>{device.user.email}</b>\n"
        f"<code>{device.device_fingerprint[:32]}</code>\n"
        "شاشة القفل تمنع الدخول الآن. إعادة الترخيص: /license."
    )


def _cmd_users(query):
    qs = User.objects.order_by('-date_joined')
    if query:
        qs = qs.filter(email__icontains=query)
    users = list(qs[:MAX_LIST])
    if not users:
        return f"لا يوجد مستخدمون مطابقون: <code>{query}</code>"
    lines = [f"👥 <b>المستخدمون ({User.objects.count()} إجمالاً):</b>\n"]
    for u in users:
        state = '✅ نشط' if u.is_active else '⛔ معطل'
        lines.append(
            f"• <b>{u.email}</b>\n"
            f"  {u.get_role_display()} — {state}"
        )
    if qs.count() > MAX_LIST:
        lines.append(f"\nو{qs.count() - MAX_LIST} أخرى… حدد البحث: /users نص")
    return "\n".join(lines)


def _cmd_stats():
    return (
        "📊 <b>إحصاءات المنصة</b>\n"
        f"👥 المستخدمون: {User.objects.count()} "
        f"(نشطون: {User.objects.filter(is_active=True).count()})\n"
        f"🏥 المرضى: {Patient.objects.count()}\n"
        f"🖥 الأجهزة: {DeviceRegistry.objects.count()} "
        f"(موثوقة: {DeviceRegistry.objects.filter(is_trusted=True).count()}, "
        f"معلقة: {DeviceRegistry.objects.filter(is_trusted=False).count()})\n"
        f"⛔ محظورة: {BlockedDevice.objects.enforceable().count()}\n"
        f"💾 النسخ الاحتياطية: {BackupRecord.objects.count()}"
    )


def _cmd_backups(limit):
    backups = BackupRecord.objects.order_by('-created_at')[
        :min(max(limit, 1), MAX_LIST)
    ]
    if not backups:
        return "لا توجد نسخ احتياطية بعد."
    lines = ["💾 <b>آخر النسخ الاحتياطية:</b>\n"]
    for b in backups:
        lines.append(
            f"• <code>{b.filename}</code>\n"
            f"  {b.get_scope_display()} — {b.size_bytes // 1024} KB — "
            f"{b.get_delivery_status_display()} — "
            f"{timezone.localtime(b.created_at).strftime('%m-%d %H:%M')}"
        )
    return "\n".join(lines)


def _cmd_backup_now(scope):
    from apps.backups.services import create_backup
    from apps.backups.models import BackupRecord as BR
    valid = {'FULL', 'DATABASE', 'MEDIA'}
    scope = (scope or 'FULL').upper()
    if scope not in valid:
        return "⚠ النطاق يجب أن يكون FULL أو DATABASE أو MEDIA"
    try:
        record = create_backup(kind=BR.Kind.MANUAL, note='telegram-command',
                               scope=scope)
    except Exception as e:
        return f"❌ فشل إنشاء النسخة: {e}"
    from apps.backups.offsite import deliver_backup
    deliver_backup(record)
    return (
        f"✅ <b>اكتملت النسخة</b>\n"
        f"<code>{record.filename}</code>\n"
        f"النطاق: {record.get_scope_display()} — {record.size_bytes // 1024} KB — "
        f"التسليم: {record.get_delivery_status_display()}"
    )


def _route_command(text):
    """Map a message to its handler. Returns the reply text."""
    parts = text.strip().split()
    cmd = parts[0].split('@')[0].lower()  # strip /cmd@botname suffix
    arg = ' '.join(parts[1:]).strip()

    simple = {
        '/start': lambda: HELP_TEXT,
        '/help': lambda: HELP_TEXT,
        '/pending': _cmd_pending,
        '/stats': _cmd_stats,
    }
    if cmd in simple:
        return simple[cmd]()

    if cmd == '/approve' and arg:
        return _cmd_approve(arg)
    if cmd == '/block' and arg:
        return _cmd_block(arg)
    if cmd == '/unblock' and arg:
        return _cmd_unblock(arg)
    if cmd == '/devices':
        return _cmd_devices(int(arg) if arg.isdigit() else 5)
    if cmd == '/licenses':
        return _cmd_licenses(int(arg) if arg.isdigit() else 5)
    if cmd == '/license' and arg:
        parts = arg.split()
        days = parts[1] if len(parts) > 1 and parts[1].isdigit() else None
        return _cmd_license(parts[0], days=days)
    if cmd == '/revoke' and arg:
        return _cmd_revoke(arg)
    if cmd == '/users':
        return _cmd_users(arg)
    if cmd == '/backups':
        return _cmd_backups(int(arg) if arg.isdigit() else 5)
    if cmd == '/backup':
        return _cmd_backup_now(arg)

    return ("❓ أمر غير معروف. الأوامر المتاحة:\n" + HELP_TEXT)


def process_update(update, request=None):
    """Process one Telegram update dict. Returns True when handled.

    Shared by the webhook view and the polling command so both paths enforce
    the same authorization and the same admin actions.
    """
    if not isinstance(update, dict):
        return False

    if 'callback_query' in update and update['callback_query']:
        return _process_callback(update['callback_query'], request)

    message = update.get('message')
    if not message:
        return False

    chat_id = (message.get('chat') or {}).get('id')
    text = (message.get('text') or '').strip()
    if not chat_id or not text.startswith('/'):
        return False

    if not _is_admin_chat(chat_id):
        from apps.security.telegram_service import _send_html
        _send_html(chat_id, UNAUTHORIZED_TEXT)
        logger.warning(
            f"TELEGRAM_UNAUTHORIZED_COMMAND chat={chat_id} text={text[:64]}"
        )
        return True

    from apps.security.telegram_service import _send_html
    try:
        reply = _route_command(text)
    except Exception as e:
        logger.exception('Telegram command failed')
        reply = f"❌ خطأ أثناء تنفيذ الأمر: {e}"
    _send_html(chat_id, reply)
    return True


def _process_callback(callback_query, request):
    """Approve/reject/deactivate button presses — shared by webhook+polling."""
    from apps.security.models import DeviceRegistry
    from apps.audit.utils import log_security_event
    from apps.security.session_security import SessionManager
    from apps.security.telegram_service import (
        answer_callback_query, edit_message_text, send_device_deactivated_notification,
    )

    data = (callback_query.get('data') or '')
    callback_id = callback_query.get('id')
    msg = callback_query.get('message') or {}
    chat_id = (msg.get('chat') or {}).get('id')
    message_id = msg.get('message_id')
    original_text = msg.get('text') or ''

    if not _is_admin_chat(chat_id):
        if callback_id:
            answer_callback_query(callback_id, 'غير مصرح', show_alert=True)
        return True

    device = None
    action = None
    for prefix in ('approve_', 'reject_', 'deactivate_'):
        if data.startswith(prefix):
            action = prefix[:-1]
            device = DeviceRegistry.objects.filter(
                id=data[len(prefix):]
            ).select_related('user').first()
            break
    if device is None:
        if callback_id:
            answer_callback_query(callback_id, 'الجهاز غير موجود', show_alert=True)
        return True

    if action == 'approve':
        device.is_trusted = True
        device.save(update_fields=['is_trusted'])
        # الموافقة عبر الأزرار تُرخّص الجهاز تلقائياً — نفس قاعدة /approve.
        from apps.security.licensing import issue_license
        license_obj, _created = issue_license(device, issued_by='telegram')
        log_security_event(
            user=device.user,
            event_type='DEVICE_APPROVED_VIA_TELEGRAM',
            request=request,
            details={'device_id': str(device.id),
                     'device_fingerprint': device.device_fingerprint,
                     'license_key': license_obj.license_key},
            severity='INFO',
        )
        from apps.security.views import _notify_user
        _notify_user(
            device.user,
            notification_type='LOGIN_ALERT',
            title='تم تفعيل جهاز جديد',
            message=(
                f'تمت الموافقة على الجهاز ({device.os_info or "جهاز"} — '
                f'بصمة: {device.device_fingerprint[:16]}…) ويمكنك تسجيل الدخول منه الآن. '
                f'إن لم تكن أنت من طلبه فأبلغ الإدارة فوراً.'
            ),
            priority='MEDIUM',
            data={'device_id': str(device.id)},
        )
        if callback_id:
            answer_callback_query(callback_id, 'تم تفعيل الجهاز بنجاح')
        if message_id is not None:
            edit_message_text(chat_id, message_id,
                              f"{original_text}\n\n✅ <b>تم تفعيل الجهاز</b>")
        return True

    if action == 'reject':
        BlockedDevice.objects.update_or_create(
            device_fingerprint=device.device_fingerprint,
            defaults={
                'reason': 'مرفوض من تيليجرام',
                'mac_address': device.mac_address,
                'is_active': True,
            },
        )
        log_security_event(
            user=device.user,
            event_type='DEVICE_REJECTED_VIA_TELEGRAM',
            request=request,
            details={'device_id': str(device.id),
                     'device_fingerprint': device.device_fingerprint},
            severity='WARNING',
        )
        from apps.security.views import _notify_user
        _notify_user(
            device.user,
            notification_type='SECURITY_ALERT',
            title='تم رفض طلب تفعيل جهاز',
            message=(
                f'رُفض الجهاز ({device.os_info or "جهاز"} — '
                f'بصمة: {device.device_fingerprint[:16]}…) وحُظر من الدخول. '
                f'إن كنت أنت من حاول الدخول فتواصل مع الإدارة لمعرفة السبب.'
            ),
            priority='HIGH',
            data={'device_id': str(device.id)},
        )
        if callback_id:
            answer_callback_query(callback_id, 'تم حظر الجهاز')
        if message_id is not None:
            edit_message_text(chat_id, message_id,
                              f"{original_text}\n\n❌ <b>تم حظر الجهاز</b>")
        return True

    # deactivate — same rule as the dashboard (via _deactivate_device)
    from apps.security.views import _deactivate_device
    _deactivate_device(device, request, via='telegram')
    if callback_id:
        answer_callback_query(callback_id, 'تم إلغاء تفعيل الجهاز وحظره')
    if message_id is not None:
        edit_message_text(chat_id, message_id,
                          f"{original_text}\n\n🔒 <b>تم إلغاء التفعيل وحظر الجهاز</b>")
    return True

