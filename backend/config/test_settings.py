# Test settings for SecureMed
# Uses SQLite for fast test execution, disables SSL for dev
import os
from datetime import timedelta
from .settings import *  # noqa

# Use SQLite for tests (faster, no PostgreSQL required)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Disable SSL for tests
for db in DATABASES.values():
    db.get('OPTIONS', {}).pop('sslmode', None)
    db.get('OPTIONS', {}).pop('sslrootcert', None)
    db.get('OPTIONS', {}).pop('sslcert', None)
    db.get('OPTIONS', {}).pop('sslkey', None)

# Mock services activation (for development without external services)
MOCK_SERVICES = os.environ.get('MOCK_SERVICES', 'false').lower() == 'true'
if MOCK_SERVICES:
    # Activate mock AI service
    from mock_services.config import MOCK_SERVICES as _MS  # noqa: F401
    # Patch AI service views to use mock
    import mock_services
    mock_service = mock_services.patch_ai_service()
    
    # Mock cache to use memory cache with predefined responses
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'test-mock',
        }
    }
    
    # Mock Redis connection for celery/broker
    try:
        import redis as _redis
        _redis_client = _redis.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379/0'), decode_responses=True)
        _redis_client.ping()
    except Exception:
        import mock_services as _ms
        from unittest.mock import MagicMock
        _redis_client = MagicMock()
        _redis_client.get.return_value = None
        _redis_client.set.return_value = True
        _redis_client.exists.return_value = False
        _redis_client.flushdb.return_value = None
        _redis_client.ping.return_value = True
