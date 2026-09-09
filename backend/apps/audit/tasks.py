from celery import shared_task
import logging
from django.contrib.auth import get_user_model

logger = logging.getLogger('security')
User = get_user_model()


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def async_save_audit_log(self, log_data):
    """Persist one audit event queued by apps.audit.utils.log_security_event.

    The row's id travels in log_data, so a retry (or the caller's synchronous
    fallback) re-runs this without inserting a second copy — audit rows are
    hash-chained and duplicates make the chain's counts meaningless.

    Failures are retried and then re-raised. Swallowing them meant a broken
    write dropped a security event with nothing but a log line to show for it,
    which is the one outcome an audit trail may not have.
    """
    from apps.audit.models import AuditLog

    data = dict(log_data)
    event_id = data.pop('id', None)
    user_id = data.pop('user_id', None)

    try:
        if event_id and AuditLog.objects.filter(pk=event_id).exists():
            return None

        user = User.objects.filter(id=user_id).first() if user_id else None
        log = AuditLog.objects.create(
            **({'id': event_id} if event_id else {}),
            user=user,
            **data
        )
        return str(log.pk)
    except Exception as exc:
        logger.error(f"Failed to asynchronously save audit log: {exc}")
        raise self.retry(exc=exc)


@shared_task
def verify_audit_chain_task(days: int = 2):
    """Scheduled tamper-evidence check of the audit hash chain.

    The management command (verify_audit_chain) is the operator-facing form;
    this wrapper runs it from Celery beat so the check actually happens
    without someone remembering to cron it. A failed chain is both logged at
    CRITICAL and pushed to the admin Telegram chat — tamper evidence that
    never surfaces is decoration.
    """
    from datetime import timedelta
    from django.utils import timezone
    from apps.audit.models import AuditLog

    since = timezone.now() - timedelta(days=days)
    result = AuditLog.verify_chain(since=since)
    logger.info(
        "AUDIT_CHAIN_CHECK checked=%s signed=%s legacy=%s unsigned=%s ok=%s",
        result['checked'], result['signed'], result['legacy'],
        result['unsigned'], result['ok'],
    )
    if not result['ok']:
        logger.critical("AUDIT_CHAIN_TAMPERED problems=%s", result['problems'])
        try:
            from apps.security.telegram_service import send_critical_alert
            problems = result['problems'][:5]
            lines = [
                f"<b>الفحص:</b> آخر {days} يوم — {result['checked']} سجل",
                f"<b>مشاكل:</b> {len(result['problems'])}",
            ]
            for p in problems:
                lines.append(
                    f"• <code>{p['id']}</code> — {p['error']}"
                )
            send_critical_alert('تلاعب محتمل في سجل التدقيق!', lines)
        except Exception as e:
            logger.error(f"Failed to send audit chain alert: {e}")
    return {'ok': result['ok'], 'checked': result['checked'],
            'problems': len(result['problems'])}


@shared_task
def send_security_digest():
    """Daily security-digest message to the admin Telegram chat.

    Declared in config/celery.py's beat schedule but never implemented — beat
    raised "Received unregistered task" every morning at 8. Summarizes the
    last 24h of audit activity by severity and top event types, plus the
    result of a quick chain check, so an operator sees the security posture
    each morning without opening the admin.
    """
    from datetime import timedelta
    from collections import Counter
    from django.db.models import Count
    from django.utils import timezone
    from apps.audit.models import AuditLog

    since = timezone.now() - timedelta(hours=24)
    qs = AuditLog.objects.filter(timestamp__gte=since)

    severity_counts = Counter(qs.values_list('severity', flat=True))
    top_events = [
        {'event': row['event_type'], 'count': row['n']}
        for row in (
            qs.values('event_type').annotate(n=Count('id'))
            .order_by('-n')[:5]
        )
    ]
    suspicious = qs.filter(
        event_type__in=[
            'LOGIN_FAILED', 'SESSION_HIJACK_DETECTED', 'SUSPICIOUS_ACTIVITY',
            'WAF_BLOCKED', 'DEVICE_REJECTED_VIA_TELEGRAM',
            'DEVICE_DEACTIVATED_VIA_TELEGRAM', 'BACKUP_DELIVERY_FAILED',
        ]
    ).count()

    chain = AuditLog.verify_chain(since=since)

    lines = [f"<b>آخر 24 ساعة</b> — {qs.count()} حدث"]
    if severity_counts:
        lines.append(
            "<b>حسب الخطورة:</b> " + "، ".join(
                f"{sev}: {n}" for sev, n in severity_counts.most_common()
            )
        )
    if top_events:
        lines.append("<b>أكثر الأحداث:</b>")
        for t in top_events:
            lines.append(f"• {t['event']} — {t['count']}")
    lines.append(f"<b>أحداث أمنية حساسة:</b> {suspicious}")
    lines.append(
        f"<b>سلامة السجل:</b> {'سليم ✓' if chain['ok'] else 'مشاكل: %d' % len(chain['problems'])}"
    )

    try:
        from apps.security.telegram_service import send_critical_alert
        send_critical_alert('الملخص الأمني اليومي', lines)
    except Exception as e:
        logger.error(f"Failed to send security digest: {e}")
    return {'events': qs.count(), 'suspicious': suspicious,
            'chain_ok': chain['ok']}
