"""
Background tasks for accounts: JWT token cleanup, security digest.
"""
from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task
def cleanup_expired_tokens():
    """Remove expired JWT tokens from the blacklist table."""
    try:
        from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
        from django.utils import timezone
        deleted, _ = OutstandingToken.objects.filter(expires_at__lt=timezone.now()).delete()
        logger.info(f'Cleaned up {deleted} expired JWT tokens')
        return {'deleted_tokens': deleted}
    except Exception as exc:
        logger.exception('Token cleanup failed')
        return {'error': str(exc)}
