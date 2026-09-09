"""
Background task wrapper for the cleanup_blocklists management command.

The command (apps.security.management.commands.cleanup_blocklists) is the
operator-facing form with --dry-run; this beat entry runs the default policy
weekly so the blacklists stay readable and long-idle devices lose their trust
without anyone remembering to schedule it.
"""
from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task
def cleanup_blocklists_task(untrust_days: int = 180):
    from io import StringIO
    from django.core.management import call_command

    out = StringIO()
    call_command(
        'cleanup_blocklists',
        untrust_days=untrust_days,
        stdout=out,
    )
    result = out.getvalue()
    logger.info(f'cleanup_blocklists completed: {result[:500]}')
    return {'status': 'success', 'output': result[:2000]}


@shared_task
def send_pending_devices_digest_task():
    """Re-send the pending-device approval queue to the admin chat daily.

    The per-device approval push happens at request time, but a Telegram
    hiccup at that moment leaves the request invisible to an admin who only
    watches the chat. Closes that loop every morning at 9.
    """
    from apps.security.models import DeviceRegistry
    from apps.security.telegram_service import send_pending_devices_digest

    pending = list(
        DeviceRegistry.objects.filter(is_trusted=False)
        .select_related('user')
        .order_by('created_at')
    )
    ok = send_pending_devices_digest(pending)
    logger.info(f'Pending-devices digest: {len(pending)} devices, sent={ok}')
    return {'pending': len(pending), 'sent': ok}
