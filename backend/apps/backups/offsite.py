"""
Off-site backup delivery: Telegram document upload and S3-compatible cloud copy.

Why both channels: the Telegram Bot API caps one document at 50 MB, so an
archive that outgrows the chat needs the bucket; and a bucket alone puts the
only copy of the database in a place an operator may not check. Either channel
can be enabled alone, both together, or neither — settings drive it, and a
deployment with neither configured keeps behaving exactly as before (local
archives only, ``delivery_status`` stays NOT_SENT).

The file is delivered exactly as it sits on disk — Fernet-encrypted by
apps.backups.services — so neither the chat nor the bucket ever holds a
readable database dump.
"""
import logging

from django.conf import settings

logger = logging.getLogger('security')


def _telegram_enabled():
    from django.conf import settings as s
    return bool(
        getattr(s, 'BACKUP_SEND_TO_TELEGRAM', False)
        and getattr(s, 'TELEGRAM_BOT_TOKEN', '')
        and getattr(s, 'TELEGRAM_ADMIN_CHAT_ID', '')
    )


def _cloud_enabled():
    from django.conf import settings as s
    return bool(
        getattr(s, 'BACKUP_OFFSITE_ENABLED', False)
        and getattr(s, 'BACKUP_OFFSITE_BUCKET', '')
        and _cloud_credentials()[0]
        and _cloud_credentials()[1]
    )


def _cloud_credentials():
    """Dedicated off-site keys first, falling back to the media-bucket keys.

    A deployment that already runs S3 media storage often wants backups in a
    different account/bucket; dedicated BACKUP_OFFSITE_* keys make that
    possible without touching AWS_ACCESS_KEY_ID.
    """
    from django.conf import settings as s
    access = (
        getattr(s, 'BACKUP_OFFSITE_ACCESS_KEY_ID', '')
        or getattr(s, 'AWS_ACCESS_KEY_ID', '')
    )
    secret = (
        getattr(s, 'BACKUP_OFFSITE_SECRET_ACCESS_KEY', '')
        or getattr(s, 'AWS_SECRET_ACCESS_KEY', '')
    )
    return access, secret


def send_to_telegram(record) -> dict:
    """Upload the encrypted archive to the admin chat. Best-effort."""
    from apps.security.telegram_service import send_backup_document
    try:
        ok = send_backup_document(record)
    except Exception as e:
        logger.error(f"Telegram backup delivery crashed: {e}")
        ok = False
    return {
        'ok': ok,
        'detail': '' if ok else 'telegram delivery failed (see security log)',
    }


def send_to_cloud(record) -> dict:
    """Copy the encrypted archive to the configured S3-compatible bucket.

    boto3's managed uploader handles multipart for large archives. Server-side
    encryption is requested per object because the archive is only client-side
    encrypted with Fernet, and bucket policies in medical settings usually
    demand SSE anyway.
    """
    import os
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError

    bucket = settings.BACKUP_OFFSITE_BUCKET
    prefix = (settings.BACKUP_OFFSITE_PREFIX or 'securemed-backups').strip('/')
    key = f'{prefix}/{record.filename}'

    if not os.path.exists(record.filepath):
        return {'ok': False, 'detail': f'missing on disk: {record.filepath}'}

    try:
        access_key, secret_key = _cloud_credentials()
        client = boto3.client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=getattr(settings, 'AWS_S3_REGION_NAME', None)
            or settings.BACKUP_OFFSITE_REGION,
            endpoint_url=getattr(settings, 'BACKUP_OFFSITE_ENDPOINT_URL', '') or None,
        )
        extra = {'ServerSideEncryption': 'AES256'}
        client.upload_file(
            record.filepath, bucket, key, ExtraArgs=extra,
        )
        return {'ok': True, 'bucket': bucket, 'key': key}
    except (BotoCoreError, ClientError) as e:
        logger.error(f"Cloud backup delivery failed: {e}")
        return {'ok': False, 'detail': str(e)[:300]}
    except Exception as e:
        logger.error(f"Cloud backup delivery crashed: {e}")
        return {'ok': False, 'detail': str(e)[:300]}


def deliver_backup(record) -> dict:
    """Run every enabled delivery channel for *record* and persist the outcome.

    Returns a summary dict; the canonical state is the BackupRecord row
    (delivery_status / delivery_detail / offsite_key / delivered_at).
    """
    from apps.backups.models import BackupRecord

    results = {'telegram': None, 'cloud': None}
    telegram_ok = False
    cloud_ok = False

    if _telegram_enabled():
        results['telegram'] = send_to_telegram(record)
        telegram_ok = bool(results['telegram']['ok'])

    if _cloud_enabled():
        results['cloud'] = send_to_cloud(record)
        cloud_ok = bool(results['cloud']['ok'])
        if cloud_ok:
            record.offsite_key = results['cloud']['key']

    ds = BackupRecord.DeliveryStatus
    if telegram_ok and cloud_ok:
        record.delivery_status = ds.BOTH
    elif telegram_ok:
        record.delivery_status = ds.TELEGRAM
    elif cloud_ok:
        record.delivery_status = ds.CLOUD
    elif _telegram_enabled() or _cloud_enabled():
        record.delivery_status = ds.FAILED
    else:
        record.delivery_status = ds.NOT_SENT

    record.delivery_detail = results
    if record.delivery_status != ds.NOT_SENT:
        from django.utils import timezone
        record.delivered_at = timezone.now()

    record.save(update_fields=[
        'delivery_status', 'delivery_detail', 'offsite_key', 'delivered_at',
    ])

    return {
        'delivery_status': record.delivery_status,
        'telegram_ok': telegram_ok,
        'cloud_ok': cloud_ok,
        'results': results,
    }
