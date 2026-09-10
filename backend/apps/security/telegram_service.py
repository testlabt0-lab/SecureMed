import requests
import logging
from django.conf import settings

logger = logging.getLogger('security')


def _send_html(title, body_html):
    """Post one HTML message to the admin chat. Shared by all alert types.

    Returns True only when Telegram accepted the message: callers decide for
    themselves whether a failure is worth raising about, and everything here is
    best-effort by design — a messaging outage must never break a login, a lab
    result or a file download.
    """
    bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
    chat_id = getattr(settings, 'TELEGRAM_ADMIN_CHAT_ID', None)

    if not bot_token or not chat_id:
        logger.warning("TELEGRAM_BOT_TOKEN or TELEGRAM_ADMIN_CHAT_ID not configured.")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": f"{title}\n\n{body_html}",
        "parse_mode": "HTML",
    }

    try:
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code != 200:
            logger.error(f"Failed to send Telegram message: {response.text}")
            return False
        return True
    except Exception as e:
        logger.error(f"Error sending Telegram message: {e}")
        return False


def send_critical_alert(title, lines):
    """Send a critical operational alert to the admin chat.

    Used for medical-critical events (a lab result flagged حرج, an urgent
    channel) and for security anomaly detections that deserve a human glance.
    `lines` is a list of already-formatted HTML strings; empty or None values
    are dropped so callers can pass optional fields freely.
    """
    body = "\n".join(line for line in lines if line)
    return _send_html(f"🚨 <b>{title}</b>", body)


def send_device_approval_request(device):
    """
    Send a message to the Telegram Admin Chat to approve a new device.
    """
    bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
    chat_id = getattr(settings, 'TELEGRAM_ADMIN_CHAT_ID', None)
    
    if not bot_token or not chat_id:
        logger.warning("TELEGRAM_BOT_TOKEN or TELEGRAM_ADMIN_CHAT_ID not configured.")
        return False
        
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    message = (
        f"🚨 <b>محاولة دخول من جهاز جديد</b>\n\n"
        f"<b>المستخدم:</b> {device.user.email}\n"
        f"<b>معرف الجهاز (Fingerprint):</b> <code>{device.device_fingerprint}</code>\n"
        f"<b>الماك أدرس:</b> <code>{device.mac_address or 'غير متوفر'}</code>\n"
        f"<b>النظام:</b> {device.os_info}\n"
        f"<b>المتصفح:</b> {device.browser_info}\n"
        f"<b>الموقع:</b> {device.location}\n"
        f"<b>IP:</b> {device.last_ip_address}\n\n"
        f"يرجى تحديد ما إذا كنت تريد السماح لهذا الجهاز."
    )
    
    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "✅ تفعيل الجهاز", "callback_data": f"approve_{device.id}"},
                {"text": "❌ حظر الجهاز", "callback_data": f"reject_{device.id}"}
            ]
        ]
    }
    
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "reply_markup": reply_markup
    }
    
    try:
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code != 200:
            logger.error(f"Failed to send Telegram message: {response.text}")
            return False
        return True
    except Exception as e:
        logger.error(f"Error sending Telegram message: {e}")
        return False

def answer_callback_query(callback_query_id, text, show_alert=False):
    bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
    if not bot_token: return
    
    url = f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery"
    requests.post(url, json={
        "callback_query_id": callback_query_id,
        "text": text,
        "show_alert": show_alert
    }, timeout=5)

def edit_message_text(chat_id, message_id, text):
    bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
    if not bot_token: return

    url = f"https://api.telegram.org/bot{bot_token}/editMessageText"
    requests.post(url, json={
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML"
    }, timeout=5)


# Hard limit of the public Bot API for one sendDocument upload (50 MB).
# Archives above it are split into parts just under the cap — see
# send_backup_document — so a Telegram-only deployment still gets every
# archive, not only the small ones.
TELEGRAM_DOCUMENT_MAX_BYTES = 50 * 1024 * 1024
# Margin subtracted from the cap per part: the multipart form framing and the
# caption travel in the same request, so a part sized exactly at the cap can
# still be rejected. 2 MB is comfortably enough and keeps part counts low.
_TELEGRAM_PART_MARGIN = 2 * 1024 * 1024


def _send_document_bytes(chat_id, filename, fileobj, caption):
    """One sendDocument call. Returns True only on a 200 from Telegram."""
    bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
    url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
    try:
        response = requests.post(
            url,
            data={"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"},
            files={"document": (filename, fileobj, "application/octet-stream")},
            timeout=300,
        )
        if response.status_code != 200:
            logger.error(f"Failed to send backup document: {response.text[:200]}")
            return False
        return True
    except Exception as e:
        logger.error(f"Error sending backup document: {e}")
        return False


def send_backup_document(record, cap_bytes=None):
    """Upload a finished (encrypted) backup archive to the admin chat.

    The file is sent exactly as it sits on disk — Fernet-encrypted by
    apps.backups.services — so an admin chat compromise never yields a
    readable database dump. Returns True only when Telegram accepted
    *everything*; every failure mode is logged and reported as False because a
    messaging outage must never break the backup run itself.

    Archives larger than the Bot API's 50 MB document cap used to be skipped
    outright, which quietly left the chat with no off-site copy at all. They
    are now split into sequential parts just under the cap
    (``<filename>.partNN-of-M``) and sent in order; concatenating the parts in
    numeric order reproduces the archive byte for byte (verify against
    record.checksum after reassembly). Each caption carries the part number so
    an operator restoring from the chat knows what to join.
    """
    bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
    chat_id = getattr(settings, 'TELEGRAM_ADMIN_CHAT_ID', None)
    if not bot_token or not chat_id:
        logger.warning("TELEGRAM_BOT_TOKEN or TELEGRAM_ADMIN_CHAT_ID not configured.")
        return False

    import os
    if not getattr(record, 'exists_on_disk', True) or not os.path.exists(record.filepath):
        logger.error(f"Backup document not on disk: {record.filepath}")
        return False

    cap = cap_bytes or TELEGRAM_DOCUMENT_MAX_BYTES
    part_size = cap - _TELEGRAM_PART_MARGIN
    size = record.size_bytes or os.path.getsize(record.filepath)

    if size > cap:
        # Split delivery. Read sequential slices so a 2 GB archive never sits
        # in memory; each part is named so its order is unambiguous.
        import math
        part_count = max(2, math.ceil(size / part_size))
        logger.info(
            f"Backup {record.filename} ({size} bytes) exceeds the Bot API "
            f"document limit — sending {part_count} parts of ≤{part_size} bytes."
        )
        width = max(2, len(str(part_count)))
        sent_parts = []
        with open(record.filepath, 'rb') as fh:
            for index in range(part_count):
                chunk = fh.read(part_size)
                if not chunk:
                    break
                part_name = (
                    f"{record.filename}.part{str(index + 1).zfill(width)}"
                    f"-of-{str(part_count).zfill(width)}"
                )
                caption = (
                    f"💾 <b>نسخة احتياطية — جزء {index + 1}/{part_count}</b>\n"
                    f"<b>الأرشيف:</b> <code>{record.filename}</code>\n"
                    f"<b>الحجم الكلي:</b> {size / 1024 / 1024:.1f} MB\n"
                    f"<b>بصمة SHA-256 للأرشيف كاملاً:</b> <code>{record.checksum[:16]}…</code>\n"
                    f"الملف مشفّر. للاستعادة: اجمع الأجزاء بالترتيب في ملف واحد "
                    f"بالاسم الأصلي ثم تحقق من البصمة."
                )
                import io
                if not _send_document_bytes(chat_id, part_name, io.BytesIO(chunk), caption):
                    logger.error(
                        f"Backup split delivery stopped at part {index + 1}/{part_count} "
                        f"of {record.filename}"
                    )
                    return False
                sent_parts.append(part_name)
        logger.info(
            f"Backup {record.filename} delivered as {len(sent_parts)} Telegram parts."
        )
        return True

    caption = (
        f"💾 <b>نسخة احتياطية</b>\n"
        f"<b>الملف:</b> <code>{record.filename}</code>\n"
        f"<b>الحجم:</b> {size / 1024:.1f} KB\n"
        f"<b>النوع:</b> {record.get_kind_display()}\n"
        f"<b>بصمة SHA-256:</b> <code>{record.checksum[:16]}…</code>\n"
        f"الملف مشفّر — لا يُفتح إلا بالمفتاح المُعدّ له."
    )
    with open(record.filepath, 'rb') as fh:
        return _send_document_bytes(chat_id, record.filename, fh, caption)


def send_backup_result_notification(record=None, success=True, detail=''):
    """Announce the outcome of an automatic backup run to the admin chat."""
    if success:
        lines = ["✅ <b>اكتمل النسخ الاحتياطي التلقائي</b>"]
        if record is not None:
            lines += [
                f"<b>الملف:</b> <code>{record.filename}</code>",
                f"<b>الحجم:</b> {record.size_bytes / 1024:.1f} KB",
                f"<b>المدة:</b> {record.duration_ms} ms",
                f"<b>حالة التسليم:</b> {record.get_delivery_status_display()}",
            ]
    else:
        lines = ["🚨 <b>فشل النسخ الاحتياطي التلقائي</b>"]
    if detail:
        lines.append(f"<code>{detail[:500]}</code>")
    return _send_html("", "\n".join(lines))


def send_device_deactivated_notification(device, by_label=''):
    """Tell the admin chat that a trusted device was deactivated (revoked)."""
    lines = [
        "🔒 <b>تم إلغاء تفعيل جهاز</b>",
        f"<b>المستخدم:</b> {device.user.email}",
        f"<b>معرف الجهاز:</b> <code>{device.device_fingerprint}</code>",
        f"<b>الماك أدرس:</b> <code>{device.mac_address or 'غير متوفر'}</code>",
    ]
    if by_label:
        lines.append(f"<b>بواسطة:</b> {by_label}")
    return _send_html("", "\n".join(lines))


def send_pending_devices_digest(devices):
    """Daily digest of devices still awaiting approval.

    An approval request is pushed the moment a device asks for it, but if
    Telegram was unreachable at that moment the request existed only in the
    database — an admin looking only at the chat would never see it. This
    digest closes that loop, with approve buttons inline (same callbacks the
    original request used), capped at 8 buttons per Telegram's keyboard size.
    """
    bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
    chat_id = getattr(settings, 'TELEGRAM_ADMIN_CHAT_ID', None)
    if not bot_token or not chat_id:
        logger.warning("TELEGRAM_BOT_TOKEN or TELEGRAM_ADMIN_CHAT_ID not configured.")
        return False

    if not devices:
        return True  # nothing pending — nothing to say

    rows = []
    for d in devices[:8]:
        rows.append([
            {"text": f"✅ {d.user.email[:24]}",
             "callback_data": f"approve_{d.id}"},
            {"text": "❌", "callback_data": f"reject_{d.id}"},
        ])

    message = (
        f"📋 <b>أجهزة بانتظار الموافقة ({len(devices)})</b>\n\n"
        + "\n".join(
            f"• <b>{d.user.email}</b>\n"
            f"  <code>{d.device_fingerprint[:32]}</code>\n"
            f"  {d.os_info or 'نظام غير معروف'} — IP: {d.last_ip_address or '؟'}"
            for d in devices[:8]
        )
    )
    if len(devices) > 8:
        message += f"\n\nو{len(devices) - 8} أخرى — راجع لوحة التحكم."

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        response = requests.post(url, json={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
            "reply_markup": {"inline_keyboard": rows},
        }, timeout=5)
        if response.status_code != 200:
            logger.error(f"Failed to send pending devices digest: {response.text[:200]}")
            return False
        return True
    except Exception as e:
        logger.error(f"Error sending pending devices digest: {e}")
        return False
