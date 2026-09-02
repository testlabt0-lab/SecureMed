"""
Django settings for SecureMed platform.
Implements all 6 security requirements from the doctor's specifications.
"""
import os
from datetime import timedelta
from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config(
    'SECRET_KEY',
    default='django-insecure-securemed-development-key-change-in-production-2026',
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config(
    'ALLOWED_HOSTS',
    default='localhost,127.0.0.1,0.0.0.0',
    cast=lambda v: [s.strip() for s in v.split(',')]
)

# Application definition
INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_extensions',
    'drf_spectacular',
    'django_filters',
    # Local apps
    'apps.basins',
    'apps.backups',
    'apps.accounts',
    'apps.channels',
    'apps.patients',
    'apps.security',
    'apps.audit',
    'apps.notifications',
    'apps.analytics',
    'apps.reports',
    'apps.appointments',
    'apps.ai',
    'apps.pharmacy',
    'apps.billing',
    'apps.lab',
    'apps.wards',
    'apps.telemedicine',
    # Celery results backend (persists task results in DB)
    'django_celery_beat',
    'django_celery_results',
    
    # WebSockets / Real-time
    'channels',
]

MIDDLEWARE = [
    # Security middleware (must be at the top)
    'django.middleware.security.SecurityMiddleware',
    # Compress JSON/HTML responses (medical lists are text-heavy —
    # ~80% smaller payloads, a direct win on mobile/cellular links)
    'django.middleware.gzip.GZipMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    # Custom WAF middleware (DB Firewall - security requirement #5)
    'apps.security.middleware.WAFMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    # CSRF middleware (security requirement #1 - Cookie flags)
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Custom audit logging
    'apps.audit.middleware.AuditLogMiddleware',
    # Custom rate limiting middleware
    'apps.security.middleware.RateLimitMiddleware',
    # Session Fingerprint security
    'apps.security.middleware.SessionSecurityMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [(config('REDIS_HOST', default='127.0.0.1'), config('REDIS_PORT', default=6379, cast=int))],
        },
    },
}

# ============================================
# Database — Security requirement #6: encrypted DV <-> DB connection
# Priority: DATABASE_URL (cloud: Neon/Render) > explicit DB_* vars (self-managed PG)
# ============================================
_DB_SSL_OPTIONS = {'sslmode': config('DB_SSLMODE', default='prefer')}
if config('DB_SSL_CLIENT_CERTS', default=False, cast=bool):
    # Mutual TLS with client certificates (self-managed PostgreSQL)
    _DB_SSL_OPTIONS.update({
        'sslrootcert': os.path.join(BASE_DIR, 'certs', 'ca.pem'),
        'sslcert': os.path.join(BASE_DIR, 'certs', 'client.pem'),
        'sslkey': os.path.join(BASE_DIR, 'certs', 'client-key.pem'),
    })

# ============================================
# Database — Security requirement #6: encrypted DV <-> DB connection
# Resolution order:
#   1. DATABASE_URL=file:...        → SQLite file (offline demo / CI)
#   2. DATABASE_URL=postgres://...  → cloud PostgreSQL (Neon / Render) with TLS
#   3. DB_ENGINE=sqlite             → local SQLite file (demo mode)
#   4. otherwise                    → explicit DB_* vars (self-managed PostgreSQL)
# ============================================
_DATABASE_URL = config('DATABASE_URL', default='')

if _DATABASE_URL.startswith(('file:', 'file://', 'sqlite:')):
    _sqlite_path = _DATABASE_URL.split(':', 1)[1].lstrip('/').lstrip('/')
    _sqlite_path = _sqlite_path if _sqlite_path.startswith('/') else '/' + _sqlite_path
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': _sqlite_path or str(BASE_DIR / 'db.sqlite3'),
        }
    }
elif _DATABASE_URL:
    import dj_database_url

    DATABASES = {
        'default': dj_database_url.parse(
            _DATABASE_URL,
            conn_max_age=config('CONN_MAX_AGE', default=600, cast=int),
            ssl_require=True,
        )
    }
    DATABASES['default']['ATOMIC_REQUESTS'] = True
elif config('DB_ENGINE', default='') == 'sqlite':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': config('DB_NAME', default=str(BASE_DIR / 'db.sqlite3')),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME', default='securemed'),
            'USER': config('DB_USER', default='postgres'),
            'PASSWORD': config('DB_PASSWORD', default='postgres'),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='5432'),
            'OPTIONS': _DB_SSL_OPTIONS,
            'ATOMIC_REQUESTS': True,
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 12}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Custom user model
AUTH_USER_MODEL = 'accounts.User'

# Internationalization
LANGUAGE_CODE = 'ar'
TIME_ZONE = 'Asia/Aden'
USE_I18N = True
USE_TZ = True

# Static files — whitenoise (compressed + immutable caching).
# CompressedStaticFilesStorage (no manifest): the SPA index.html references
# Vite-fingerprinted assets by literal URL, so a manifest storage would 404 them.
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

# Built SPA (served by Django in production — single-service deploy)
FRONTEND_DIST = Path(config('FRONTEND_DIST', default=str(BASE_DIR.parent / 'frontend' / 'dist')))
TEMPLATES[0]['DIRS'] = [BASE_DIR / 'templates', FRONTEND_DIST]
STATICFILES_DIRS = [str(FRONTEND_DIST)] if FRONTEND_DIST.exists() else []

# Media files (uploaded files)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# File upload settings
DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024  # 20MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024  # 20MB
FILE_UPLOAD_PERMISSIONS = 0o644

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ============================================
# SECURITY SETTINGS - All 6 requirements
# ============================================

# Security requirement #1: Secure Cookie flags
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Strict'
SESSION_COOKIE_AGE = 3600  # 1 hour
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# HTTPS settings (env-overridable for local production verification)
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=not DEBUG, cast=bool)
SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=31536000, cast=int)  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_REFERRER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'

# CORS (restricted)
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:3000,http://127.0.0.1:3000',
    cast=lambda v: [s.strip() for s in v.split(',')]
)
CORS_ALLOW_CREDENTIALS = True

# CSRF origins (Django 4+ requires scheme); auto-derive from ALLOWED_HOSTS
# (a leading-dot host like ".onrender.com" becomes the wildcard "*.onrender.com")
_CSRF_ENV = config('CSRF_TRUSTED_ORIGINS', default='').strip()
if _CSRF_ENV:
    CSRF_TRUSTED_ORIGINS = [s.strip() for s in _CSRF_ENV.split(',') if s.strip()]
else:
    CSRF_TRUSTED_ORIGINS = [
        'https://' + ('*' + h if h.startswith('.') else h)
        for h in ALLOWED_HOSTS if h not in ('*',)
    ]

# ============================================
# REST Framework + JWT (Security requirement #3: Encrypted tokens)
# ============================================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'apps.security.pagination.SecureMedPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'anon': '20/hour',
        'user': '1000/hour',
        'biometric': '10/minute',
        'password_reset': '5/hour',
    },
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
}

# JWT — RS256 (asymmetric) when PEM keypair exists; graceful HS256 fallback
# so cloud deploys work without shipping private keys in the image.
_JWT_PRIV = BASE_DIR / 'certs' / 'jwt_private.pem'
_JWT_PUB = BASE_DIR / 'certs' / 'jwt_public.pem'
_JWT_ALGO = config('JWT_ALGORITHM', default='RS256' if _JWT_PRIV.exists() else 'HS256')

_JWT_BASE = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'TOKEN_TYPE_CLAIM': 'token_type',
    'JTI_CLAIM': 'jti',
}
if _JWT_ALGO == 'RS256' and _JWT_PRIV.exists() and _JWT_PUB.exists():
    SIMPLE_JWT = {
        **_JWT_BASE,
        'ALGORITHM': 'RS256',  # Asymmetric encryption
        'SIGNING_KEY': config('JWT_PRIVATE_KEY_PATH', default=str(_JWT_PRIV)),
        'VERIFYING_KEY': config('JWT_PUBLIC_KEY_PATH', default=str(_JWT_PUB)),
    }
else:
    SIMPLE_JWT = {
        **_JWT_BASE,
        'ALGORITHM': 'HS256',
        'SIGNING_KEY': config('JWT_SIGNING_KEY', default=SECRET_KEY),
    }

# ============================================
# Security requirement #6: Encryption at rest (DV <-> DB)
# ============================================
ENCRYPTION_KEY = config(
    'ENCRYPTION_KEY',
    default='securemed-field-encryption-key-32-bytes!!',  # 32 bytes for AES-256
)
USE_FIELD_ENCRYPTION = True

# Biometric authentication settings
BIOMETRIC_SETTINGS = {
    'CHALLENGE_TTL_SECONDS': 60,
    'MAX_FAILED_ATTEMPTS': 5,
    'LOCKOUT_DURATION_MINUTES': 30,
    'HASH_ALGORITHM': 'sha256',
}

# ============================================
# Backup mechanism (plan requirement: آلية النسخ الاحتياطي)
# ============================================
BACKUP_DIR = Path(config('BACKUP_DIR', default=str(BASE_DIR / 'backups')))
BACKUP_KEEP_COUNT = config('BACKUP_KEEP_COUNT', default=14, cast=int)

# Cache — Redis when REDIS_URL is set (multi-worker production),
# otherwise a file-based shared cache: correct for gunicorn's multiple
# workers (rate limits & throttles stay coherent across processes) and
# accepted by django-ratelimit (locmem is rejected as non-shared).
# Cache logic is configured at the bottom of the file with Celery settings

# Rate limiting
# DRF throttling (DEFAULT_THROTTLE_RATES above) + the custom security
# middleware implement rate limiting on the shared cache backend.
# NOTE: the unused `django_ratelimit` package was removed — its system
# check (E003) rejected every cache backend available without Redis.

# Email (for notifications)
# Production: set EMAIL_HOST (+ user/pass) via env → real SMTP.
# Fallback:   console backend prints emails to stdout.
EMAIL_HOST = config('EMAIL_HOST', default='')
if EMAIL_HOST:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=False, cast=bool)
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='SecureMed <noreply@securemed.app>')
# Used when EMAIL_BACKEND=filebased (dev/demo): real .eml files land here
EMAIL_FILE_PATH = BASE_DIR / 'logs' / 'emails'

# Password reset flow
# How long a reset link stays valid (seconds) — 1 hour is a good balance.
PASSWORD_RESET_TIMEOUT = config('PASSWORD_RESET_TIMEOUT', default=3600, cast=int)
# Frontend base URL used inside the reset link (dev: Vite server, prod: same origin)
FRONTEND_URL = config('FRONTEND_URL', default='http://localhost:3000')

# AI microservice (clinical summaries + assistant), server-to-server
AI_SERVICE_URL = config('AI_SERVICE_URL', default='http://127.0.0.1:8100')

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'security': {
            'format': '[SECURITY] {asctime} {levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'security_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'security.log',
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 5,
            'formatter': 'security',
        },
    },
    'loggers': {
        'security': {
            'handlers': ['security_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# Ensure runtime-writable dirs exist (cloud containers start with a clean FS)
os.makedirs(BASE_DIR / 'logs', exist_ok=True)
os.makedirs(BASE_DIR / 'media', exist_ok=True)
os.makedirs(BASE_DIR / 'logs' / 'emails', exist_ok=True)

# SPECTACULAR (API Documentation)
SPECTACULAR_SETTINGS = {
    'TITLE': 'SecureMed API',
    'DESCRIPTION': 'Secure Healthcare Records Management Platform with DevSecOps',
    'VERSION': '2.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
}

# Initial superuser (for setup)
INITIAL_ADMIN_USERNAME = config('INITIAL_ADMIN_USERNAME', default='admin')
INITIAL_ADMIN_PASSWORD = config('INITIAL_ADMIN_PASSWORD', default='ChangeMe@2026!')
INITIAL_ADMIN_EMAIL = config('INITIAL_ADMIN_EMAIL', default='admin@securemed.app')

# ==========================================================================
# Celery Configuration
# ==========================================================================
REDIS_URL = config('REDIS_URL', default='redis://localhost:6379/0')

CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://127.0.0.1:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://127.0.0.1:6379/0')

# AI Settings
GEMINI_API_KEY = config('GEMINI_API_KEY', default='')

CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Riyadh'
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 300   # 5 minutes max per task
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # Fair task distribution

# Cache (Redis for sessions, rate-limiting, Celery-adjacent caching)
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'IGNORE_EXCEPTIONS': True,   # Degrade gracefully if Redis is down
        },
        'KEY_PREFIX': 'securemed',
        'TIMEOUT': 300,  # 5 minutes default
    }
}
