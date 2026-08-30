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

# Test settings
DEBUG = False
SECRET_KEY = 'test-secret-key-not-for-production'
ALLOWED_HOSTS = ['*']

# Disable SSL redirect and secure cookies for tests
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_PROXY_SSL_HEADER = None

# Use HMAC for JWT in tests (no PEM file needed)
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

# Relax anonymous throttles so a test suite hitting the same endpoints
# from the same test-client IP does not trip rate limits mid-run.
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    'DEFAULT_THROTTLE_RATES': {
        **REST_FRAMEWORK.get('DEFAULT_THROTTLE_RATES', {}),
        'anon': '10000/hour',
        'password_reset': '10000/hour',
    },
}

# Disable rate limiting in tests
RATELIMIT_ENABLE = False

# Use in-memory cache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'test',
    }
}

# Remove django_ratelimit from INSTALLED_APPS to avoid cache check
INSTALLED_APPS = [app for app in INSTALLED_APPS if app != 'django_ratelimit']
# Remove ratelimit from MIDDLEWARE
MIDDLEWARE = [m for m in MIDDLEWARE if 'ratelimit' not in m.lower()]

# Faster password hashing for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable migrations for speed (creates tables directly)
class DisableMigrations:
    def __contains__(self, item):
        return True
    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()
