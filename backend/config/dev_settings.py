"""
Dev settings for running SecureMed locally without PostgreSQL.
Uses SQLite for easy testing.
"""
import os
from datetime import timedelta
from .settings import *  # noqa

# Use SQLite for dev (no PostgreSQL required)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Disable SSL for dev
for db in DATABASES.values():
    db.get('OPTIONS', {}).pop('sslmode', None)
    db.get('OPTIONS', {}).pop('sslrootcert', None)
    db.get('OPTIONS', {}).pop('sslcert', None)
    db.get('OPTIONS', {}).pop('sslkey', None)

# Dev settings
DEBUG = True
SECRET_KEY = 'dev-secret-key-not-for-production'
ALLOWED_HOSTS = ['*']

# Disable SSL redirect for dev
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_PROXY_SSL_HEADER = None

# Use HMAC for JWT in dev (no PEM file needed)
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'TOKEN_TYPE_CLAIM': 'token_type',
    'JTI_CLAIM': 'jti',
}

# Remove django_ratelimit (locmem cache warning)
INSTALLED_APPS = [app for app in INSTALLED_APPS if app != 'django_ratelimit']
MIDDLEWARE = [m for m in MIDDLEWARE if 'ratelimit' not in m.lower()]

# Use in-memory cache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'dev',
    }
}

# Activate mock services for development (simulates AI, Redis, etc.)
MOCK_SERVICES = os.environ.get('MOCK_SERVICES', 'true').lower() == 'true'
if MOCK_SERVICES:
    from mock_services.config import MOCK_SERVICES as _MS  # noqa: F401
    # Patch AI service to use mock
    import mock_services
    mock_service = mock_services.patch_ai_service()
    
    # Mock cache with predefined responses for common operations
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'dev-mock',
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
    
    # Mock email backend - just record emails without sending
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Dev email backend: write real .eml files to backend/logs/emails/
# (demonstrates the full email flow — templating, attachments — without
# SMTP credentials; set EMAIL_HOST env to switch to real SMTP)
EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
EMAIL_FILE_PATH = BASE_DIR / 'logs' / 'emails'
