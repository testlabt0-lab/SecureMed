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
