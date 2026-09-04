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
        from django.core.management import call_command
        import sys
        from io import StringIO
        
        out = StringIO()
        sys.stdout = out
        call_command('flushexpiredtokens')
        sys.stdout = sys.__stdout__
        
        output = out.getvalue().strip()
        logger.info(f'Token cleanup: {output}')
        return {'status': 'success', 'output': output}
    except Exception as exc:
        logger.exception('Token cleanup failed')
        return {'error': str(exc)}
