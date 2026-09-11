"""
Django settings for SecureMed platform.
Implements all 6 security requirements from the doctor's specifications.
"""
import os
from datetime import timedelta
from pathlib import Path
from urllib .parse import urlparse
from decouple import config

BASE_DIR =Path (__file__ ).resolve ().parent .parent 

# SECURITY WARNING: keep the secret key used in production secret!
DEBUG = config('DEBUG', default=False, cast=bool)

if DEBUG:
    SECRET_KEY = config('SECRET_KEY', default='django-insecure-securemed-development-key-change-in-production-2026')
else:
    SECRET_KEY = config('SECRET_KEY')


ALLOWED_HOSTS = config(
    'ALLOWED_HOSTS',
    default='localhost,127.0.0.1,0.0.0.0',
    cast=lambda v: [s.strip() for s in v.split(',')]
)

# Automatically allow all hosts in Railway environments to permit internal health checks
if config('RAILWAY_ENVIRONMENT_ID', default=''):
    if '*' not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append('*')

# Automatically allow Render external hostname
render_host = config('RENDER_EXTERNAL_HOSTNAME', default='')
if render_host and render_host not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(render_host)

# Application definition
INSTALLED_APPS =[
'unfold', # Must be before django.contrib.admin
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
'apps.interoperability',
# Celery results backend (persists task results in DB)
'django_celery_beat',
'django_celery_results',

# WebSockets / Real-time
'channels',
'django_prometheus',
'storages',
]

UNFOLD = {
    "SITE_TITLE": "SecureMed Admin",
    "SITE_HEADER": "SecureMed Platform",
    "SITE_URL": "/",
    "DASHBOARD_CALLBACK": "apps.analytics.admin_dashboard.dashboard_callback",
    "COLORS": {
        "primary": {
            "50": "240 253 250",
            "100": "204 251 241",
            "200": "153 246 228",
            "300": "94 234 212",
            "400": "45 212 191",
            "500": "20 184 166",
            "600": "13 148 136",
            "700": "15 118 110",
            "800": "17 94 89",
            "900": "19 78 74",
            "950": "4 47 46",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
    },
}

MIDDLEWARE =[
'django_prometheus.middleware.PrometheusBeforeMiddleware',
# Security middleware (must be at the top)
'django.middleware.security.SecurityMiddleware',
'apps.security.middleware.ZeroTrustConsentFirewallMiddleware',
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
'django_prometheus.middleware.PrometheusAfterMiddleware',
]

ROOT_URLCONF ='config.urls'

TEMPLATES =[
{
'BACKEND':'django.template.backends.django.DjangoTemplates',
'DIRS':[BASE_DIR /'templates'],
'APP_DIRS':True ,
'OPTIONS':{
'context_processors':[
'django.template.context_processors.debug',
'django.template.context_processors.request',
'django.contrib.auth.context_processors.auth',
'django.contrib.messages.context_processors.messages',
],
},
},
]

WSGI_APPLICATION ='config.wsgi.application'
ASGI_APPLICATION ='config.asgi.application'

# NOTE: CHANNEL_LAYERS is configured together with CACHES further down, once
# REDIS_URL is known (an in-memory layer cannot broadcast between workers).

# ============================================
# Database — Security requirement #6: encrypted DV <-> DB connection
# Priority: DATABASE_URL (cloud: Neon/Render) > explicit DB_* vars (self-managed PG)
# ============================================
_DB_SSL_OPTIONS ={'sslmode':config ('DB_SSLMODE',default ='require')}
if config ('DB_SSL_CLIENT_CERTS',default =False ,cast =bool ):
# Mutual TLS with client certificates (self-managed PostgreSQL)
    _DB_SSL_OPTIONS .update ({
    'sslrootcert':os .path .join (BASE_DIR ,'certs','ca.pem'),
    'sslcert':os .path .join (BASE_DIR ,'certs','client.pem'),
    'sslkey':os .path .join (BASE_DIR ,'certs','client-key.pem'),
    })

    # ============================================
    # Database — Security requirement #6: encrypted DV <-> DB connection
    # Resolution order:
    #   1. DATABASE_URL=file:...        → SQLite file (offline demo / CI)
    #   2. DATABASE_URL=postgres://...  → cloud PostgreSQL (Neon / Render) with TLS
    #   3. DB_ENGINE=sqlite             → local SQLite file (demo mode)
    #   4. otherwise                    → explicit DB_* vars (self-managed PostgreSQL)
    # ============================================
_DATABASE_URL =config ('DATABASE_URL',default ='')

if _DATABASE_URL .startswith (('file:','file://','sqlite:')):
    _sqlite_path =_DATABASE_URL .split (':',1 )[1 ].lstrip ('/').lstrip ('/')
    _sqlite_path =_sqlite_path if _sqlite_path .startswith ('/')else '/'+_sqlite_path 
    DATABASES ={
    'default':{
    'ENGINE':'django.db.backends.sqlite3',
    'NAME':_sqlite_path or str (BASE_DIR /'db.sqlite3'),
    }
    }
elif _DATABASE_URL :
    import dj_database_url 

    DATABASES ={
    'default':dj_database_url .parse (
    _DATABASE_URL ,
    conn_max_age =config ('CONN_MAX_AGE',default =600 ,cast =int ),
    ssl_require =True ,
    )
    }
    DATABASES ['default']['ATOMIC_REQUESTS']=True 
elif config ('DB_ENGINE',default ='')=='sqlite':
    DATABASES ={
    'default':{
    'ENGINE':'django.db.backends.sqlite3',
    'NAME':config ('DB_NAME',default =str (BASE_DIR /'db.sqlite3')),
    }
    }
else :
    DATABASES ={
    'default':{
    'ENGINE':'django.db.backends.postgresql',
    'NAME':config ('DB_NAME',default ='securemed'),
    'USER':config ('DB_USER',default ='postgres'),
    'PASSWORD':config ('DB_PASSWORD',default ='postgres'),
    'HOST':config ('DB_HOST',default ='localhost'),
    'PORT':config ('DB_PORT',default ='5432'),
    'OPTIONS':_DB_SSL_OPTIONS ,
    'ATOMIC_REQUESTS':True ,
    }
    }

    # Password validation
AUTH_PASSWORD_VALIDATORS =[
{'NAME':'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
{'NAME':'django.contrib.auth.password_validation.MinimumLengthValidator',
'OPTIONS':{'min_length':12 }},
{'NAME':'django.contrib.auth.password_validation.CommonPasswordValidator'},
{'NAME':'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Custom user model
AUTH_USER_MODEL ='accounts.User'

# Internationalization
LANGUAGE_CODE ='ar'
TIME_ZONE ='Asia/Aden'
USE_I18N =True 
USE_TZ =True 

# Static files — whitenoise (compressed + immutable caching).
# CompressedStaticFilesStorage (no manifest): the SPA index.html references
# Vite-fingerprinted assets by literal URL, so a manifest storage would 404 them.
STATIC_URL ='/static/'
STATIC_ROOT =BASE_DIR /'staticfiles'

# Built SPA (served by Django in production — single-service deploy)
FRONTEND_DIST =Path (config ('FRONTEND_DIST',default =str (BASE_DIR .parent /'frontend'/'dist')))
TEMPLATES [0 ]['DIRS']=[BASE_DIR /'templates',FRONTEND_DIST ]
STATICFILES_DIRS =[str (FRONTEND_DIST )]if FRONTEND_DIST .exists ()else []

# Media files (uploaded files)
MEDIA_URL ='/media/'
MEDIA_ROOT =BASE_DIR /'media'

# NOTE: storage backends (whitenoise / S3) are configured in a single STORAGES
# block near the bottom of this file, after the production hardening section.


# File upload settings
DATA_UPLOAD_MAX_MEMORY_SIZE =20 *1024 *1024 # 20MB
FILE_UPLOAD_MAX_MEMORY_SIZE =20 *1024 *1024 # 20MB
FILE_UPLOAD_PERMISSIONS =0o644 

# Default primary key field type
DEFAULT_AUTO_FIELD ='django.db.models.BigAutoField'

# ============================================
# SECURITY SETTINGS - All 6 requirements
# ============================================

# Security requirement #1: Secure Cookie flags
SESSION_COOKIE_SECURE =True 
SESSION_COOKIE_HTTPONLY =True 
SESSION_COOKIE_SAMESITE ='Strict'
CSRF_COOKIE_SECURE =True 
CSRF_COOKIE_HTTPONLY =True 
CSRF_COOKIE_SAMESITE ='Strict'
SESSION_COOKIE_AGE =3600 # 1 hour
SESSION_EXPIRE_AT_BROWSER_CLOSE =True 

# HTTPS settings (env-overridable for local production verification)
SECURE_SSL_REDIRECT =config ('SECURE_SSL_REDIRECT',default =not DEBUG ,cast =bool )
SECURE_HSTS_SECONDS =config ('SECURE_HSTS_SECONDS',default =31536000 ,cast =int )# 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS =True 
SECURE_HSTS_PRELOAD =True 
SECURE_PROXY_SSL_HEADER =('HTTP_X_FORWARDED_PROTO','https')
SECURE_CONTENT_TYPE_NOSNIFF =True 
SECURE_BROWSER_XSS_FILTER =True 
SECURE_REFERRER_POLICY ='same-origin'
X_FRAME_OPTIONS ='DENY'

# CORS (restricted)
CORS_ALLOWED_ORIGINS =config (
'CORS_ALLOWED_ORIGINS',
default ='http://localhost:3000,http://127.0.0.1:3000',
cast =lambda v :[s .strip ()for s in v .split (',')]
)
CORS_ALLOW_CREDENTIALS =True 

# CSRF origins (Django 4+ requires scheme); auto-derive from ALLOWED_HOSTS
# (a leading-dot host like ".onrender.com" becomes the wildcard "*.onrender.com")
_CSRF_ENV =config ('CSRF_TRUSTED_ORIGINS',default ='').strip ()
if _CSRF_ENV :
    CSRF_TRUSTED_ORIGINS =[s .strip ()for s in _CSRF_ENV .split (',')if s .strip ()]
else :
    CSRF_TRUSTED_ORIGINS =[
    'https://'+('*'+h if h .startswith ('.')else h )
    for h in ALLOWED_HOSTS if h not in ('*',)
    ]

    # ============================================
    # REST Framework + JWT (Security requirement #3: Encrypted tokens)
    # ============================================
REST_FRAMEWORK ={
'DEFAULT_AUTHENTICATION_CLASSES':(
'apps.security.authentication.BoundJWTAuthentication',
),
'DEFAULT_PERMISSION_CLASSES':(
'rest_framework.permissions.IsAuthenticated',
),
'DEFAULT_PAGINATION_CLASS':'apps.security.pagination.SecureMedPagination',
'PAGE_SIZE':20 ,
'DEFAULT_THROTTLE_CLASSES':(
'rest_framework.throttling.AnonRateThrottle',
'rest_framework.throttling.UserRateThrottle',
),
'DEFAULT_THROTTLE_RATES':{
'anon':'20/hour',
'user':'1000/hour',
'login':'5/minute',
'biometric':'10/minute',
        'password_reset':'5/hour',
        'device_check':'30/minute',
},
'DEFAULT_RENDERER_CLASSES':(
'rest_framework.renderers.JSONRenderer',
),
'DEFAULT_SCHEMA_CLASS':'drf_spectacular.openapi.AutoSchema',
'DEFAULT_FILTER_BACKENDS':(
'django_filters.rest_framework.DjangoFilterBackend',
'rest_framework.filters.SearchFilter',
'rest_framework.filters.OrderingFilter',
),
'DEFAULT_PARSER_CLASSES':(
'apps.security.parsers.SanitizedJSONParser',
'rest_framework.parsers.FormParser',
'rest_framework.parsers.MultiPartParser'
),
}

# ---------- JWT signing keys ----------
# RS256 when a keypair exists under backend/certs/, HS256 (SECRET_KEY) otherwise.
#
# The two settings below are *paths*; PyJWT wants the PEM *contents*. Passing the
# path is what this file used to do, and it does not degrade gracefully:
# jwt.encode(..., key='/app/backend/certs/jwt_private.pem', algorithm='RS256')
# hands those few dozen bytes to load_pem_private_key, which raises InvalidKeyError,
# so *every* token issuance — every login, every refresh — answered 500. It went
# unnoticed because certs/ does not exist on Render, so cloud deploys silently took
# the HS256 branch; the breakage appeared only on machines where
# scripts/generate_certificates.py had been run, i.e. exactly the ones opting into
# RS256 on purpose.
#
# The PEM ends up inside SIMPLE_JWT. Django's exception reporter cleanses dict keys
# matching KEY/SECRET/TOKEN recursively, and 'SIGNING_KEY' matches, so it is not
# rendered on error pages — but keep MEDIA/static serving away from certs/ all the
# same (the generator writes the private key 0600).
def _jwt_key_path(env_name, filename):
    """Path from env, resolved against BASE_DIR when relative.

    .env.example documents these as `certs/jwt_private.pem`, and a bare relative
    path resolves against the *process* cwd: correct for `manage.py` run inside
    backend/, wrong for gunicorn under the Docker image (WORKDIR /app), where the
    same value points at a file that is not there.
    """
    raw = config(env_name, default='')
    if not raw:
        return BASE_DIR / 'certs' / filename
    path = Path(raw)
    return path if path.is_absolute() else BASE_DIR / path


_JWT_PRIV = _jwt_key_path('JWT_PRIVATE_KEY_PATH', 'jwt_private.pem')
_JWT_PUB = _jwt_key_path('JWT_PUBLIC_KEY_PATH', 'jwt_public.pem')
_JWT_ALGO = config('JWT_ALGORITHM', default='RS256' if _JWT_PRIV.exists() else 'HS256')
# Only true when RS256 was asked for explicitly. The guard at the end of this file
# refuses to boot in that case rather than quietly downgrading the deployment to
# HS256 behind the operator's back.
_JWT_RS256_REQUESTED = config('JWT_ALGORITHM', default='') == 'RS256'


def _read_pem(path):
    """Return (pem_contents, error_message). Never returns the path itself."""
    try:
        text = path.read_text(encoding='utf-8').strip()
    except OSError as exc:
        return '', f'cannot read {path}: {exc.strerror or exc}'
    if '-----BEGIN' not in text:
        return '', f'{path} does not contain a PEM block'
    return text, ''


if _JWT_ALGO == 'RS256':
    _JWT_SIGNING_PEM, _jwt_priv_err = _read_pem(_JWT_PRIV)
    _JWT_VERIFYING_PEM, _jwt_pub_err = _read_pem(_JWT_PUB)
    _JWT_RS256_ERROR = _jwt_priv_err or _jwt_pub_err
else:
    _JWT_SIGNING_PEM = _JWT_VERIFYING_PEM = ''
    _JWT_RS256_ERROR = ''

_JWT_BASE ={
'ACCESS_TOKEN_LIFETIME':timedelta (minutes =15 ),
'REFRESH_TOKEN_LIFETIME':timedelta (days =1 ),
'ROTATE_REFRESH_TOKENS':True ,
'BLACKLIST_AFTER_ROTATION':True ,
'AUTH_HEADER_TYPES':('Bearer',),
'USER_ID_FIELD':'id',
'USER_ID_CLAIM':'user_id',
'TOKEN_TYPE_CLAIM':'token_type',
'JTI_CLAIM':'jti',
}
if _JWT_ALGO == 'RS256' and _JWT_SIGNING_PEM and _JWT_VERIFYING_PEM:
    SIMPLE_JWT = {
        **_JWT_BASE,
        'ALGORITHM': 'RS256',
        # PEM contents, not paths — see the note above.
        'SIGNING_KEY': _JWT_SIGNING_PEM,
        'VERIFYING_KEY': _JWT_VERIFYING_PEM,
    }
else:
    SIMPLE_JWT = {
        **_JWT_BASE,
        'ALGORITHM': 'HS256',
        # Symmetric: SimpleJWT verifies with SIGNING_KEY, so no VERIFYING_KEY here.
        'SIGNING_KEY': config('JWT_SIGNING_KEY', default=SECRET_KEY),
    }

    # ============================================
    # Security requirement #6: Encryption at rest (DV <-> DB)
    # ============================================
ENCRYPTION_KEY =config (
'ENCRYPTION_KEY',
default ='securemed-field-encryption-key-32-bytes!!',# 32 bytes for AES-256
)
FIELD_ENCRYPTION_SALT = config('FIELD_ENCRYPTION_SALT', default='securemed_salt_v1').encode('utf-8')
USE_FIELD_ENCRYPTION =True

# Retired encryption keys, newest first, comma-separated.
#
# ENCRYPTION_KEY protects patient names, national IDs, record text and — since
# ENCRYPT_MEDIA_AT_REST — the files under MEDIA_ROOT. Until now it had no rotation
# path: the key was derived straight into a single Fernet, so changing it turned
# every encrypted value into undecryptable bytes with no way back. Which is exactly
# what a responsible operator would do on the first suspicion of a leak.
#
# apps.security.crypto now encrypts with ENCRYPTION_KEY and decrypts with it *or*
# any key listed here, so rotation is:
#   1. move the current ENCRYPTION_KEY value to the front of this list
#   2. set the new key as ENCRYPTION_KEY, deploy — reads keep working immediately
#   3. re-encrypt at leisure, then remove the old key from this list
ENCRYPTION_KEY_FALLBACKS =[
k .strip ()for k in config ('ENCRYPTION_KEY_FALLBACKS',default ='').split (',')if k .strip ()
]

# Encrypt uploaded files on disk (AES-256-GCM, see apps.core.storage).
#
# Defaults to on whenever DEBUG is off, so a deployment does not have to opt in to
# protecting patient files. Reads detect encryption per file rather than consulting
# this flag, so switching it off stops encrypting *new* uploads without orphaning
# anything already stored. Ignored when files live in S3, where server-side
# encryption and signed URLs already cover this.
ENCRYPT_MEDIA_AT_REST =config ('ENCRYPT_MEDIA_AT_REST',default =not DEBUG ,cast =bool )

# Key that signs the audit log hash chain (apps.audit.models.AuditLog).
# Kept separate from SECRET_KEY on purpose: SECRET_KEY is used for sessions, tokens
# and password reset links, so it is handled by more code and rotated for reasons
# that have nothing to do with the audit trail. Rotating SECRET_KEY would silently
# invalidate every historical audit signature, and leaking it would hand over the
# ability to forge audit history. Empty means "fall back to SECRET_KEY", which keeps
# an existing deployment signing rather than not signing at all.
AUDIT_LOG_HMAC_KEY =config ('AUDIT_LOG_HMAC_KEY',default ='')

# Audit events are normally handed to Celery so the request does not pay for the
# insert. That is only safe where a worker is actually running: `.delay()` succeeds
# as soon as the broker accepts the message, so a deployment with a reachable Redis
# but no worker process queues every audit event and writes none of them — silently,
# and with no error anywhere. Set AUDIT_LOG_ASYNC=False on single-service
# deployments (no worker) to write audit rows inline instead.
AUDIT_LOG_ASYNC =config ('AUDIT_LOG_ASYNC',default =True ,cast =bool )

# Biometric / WebAuthn login knobs. Only keys that something actually reads belong
# here: a dial that changes nothing is worse than no dial, because an operator turns
# it and believes the policy changed.
#
# Removed for that reason:
#   * HASH_ALGORITHM — belonged to the deleted hash_biometric() shared-secret
#     scheme. Login is an EC P-256 signature over a server challenge now; the digest
#     is fixed by the algorithm, not configurable.
#   * LOCKOUT_DURATION_MINUTES — never read. User.lock_account() applies exponential
#     backoff (5 min doubling per failure past the third, capped at 1440), so setting
#     this to 60 bought an operator nothing but a false sense of the real policy.
BIOMETRIC_SETTINGS ={
'CHALLENGE_TTL_SECONDS':60 ,
'MAX_FAILED_ATTEMPTS':5 ,
}
# WebAuthn relying-party settings live further down, right after FRONTEND_URL,
# because they are derived from it.

# Expected response is HMAC of challenge with a session key
ADAPTIVE_MFA_ENABLED = True

# Reverse-geocoding of login IPs. Off by default: it sends the address of every
# user who logs in to an unaffiliated third party, and the only thing the result
# is used for is the "new location" label on a DeviceRegistry row. Turn it on
# only where that disclosure has been reviewed. See apps.audit.device_tracker.
GEOIP_LOOKUP_ENABLED =config ('GEOIP_LOOKUP_ENABLED',default =False ,cast =bool )
GEOIP_LOOKUP_URL =config ('GEOIP_LOOKUP_URL',default ='https://ip-api.com/json/{ip}')

# Backup mechanism (plan requirement: آلية النسخ الاحتياطي)
# ============================================
BACKUP_DIR =Path (config ('BACKUP_DIR',default =str (BASE_DIR /'backups')))
BACKUP_KEEP_COUNT =config ('BACKUP_KEEP_COUNT',default =14 ,cast =int )
# Fernet key for encrypting backup archives at rest (AES-128-CBC + HMAC under
# the hood). Falls back to SECRET_KEY so an existing deployment keeps producing
# restorable archives, but a dedicated key means whoever leaks SECRET_KEY does
# not automatically get every backup with it.
BACKUP_ENCRYPTION_KEY =config ('BACKUP_ENCRYPTION_KEY',default ='')

# Off-site delivery of every finished archive (خطة النسخ التلقائي عبر تلجرام
# أو التخزين السحابي). Both channels are opt-in; a deployment with neither
# configured keeps local-only archives as before.
#
# 1. Telegram: the encrypted archive is uploaded to the admin chat via
#    sendDocument. The public Bot API caps one document at 50 MB — larger
#    archives simply skip this channel, so pair it with the bucket for big
#    databases. Requires TELEGRAM_BOT_TOKEN + TELEGRAM_ADMIN_CHAT_ID.
BACKUP_SEND_TO_TELEGRAM =config ('BACKUP_SEND_TO_TELEGRAM',default =False ,cast =bool )
# 2. Cloud: a copy is pushed to any S3-compatible bucket (AWS S3, Cloudflare
#    R2, Backblaze B2, MinIO, Spaces) with boto3, multipart-safe. Credentials
#    default to AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY; set
#    BACKUP_OFFSITE_ENDPOINT_URL for non-AWS endpoints.
BACKUP_OFFSITE_ENABLED =config ('BACKUP_OFFSITE_ENABLED',default =False ,cast =bool )
BACKUP_OFFSITE_BUCKET =config ('BACKUP_OFFSITE_BUCKET',default ='')
BACKUP_OFFSITE_PREFIX =config ('BACKUP_OFFSITE_PREFIX',default ='securemed-backups')
BACKUP_OFFSITE_ENDPOINT_URL =config ('BACKUP_OFFSITE_ENDPOINT_URL',default ='')
BACKUP_OFFSITE_REGION =config ('BACKUP_OFFSITE_REGION',default ='us-east-1')
BACKUP_OFFSITE_ACCESS_KEY_ID =config ('BACKUP_OFFSITE_ACCESS_KEY_ID',default ='')
BACKUP_OFFSITE_SECRET_ACCESS_KEY =config ('BACKUP_OFFSITE_SECRET_ACCESS_KEY',default ='')

# ============================================
# Telegram device-approval bot
# ============================================
# New devices are held untrusted until an admin taps Approve in the admin chat.
# Leave both empty to disable the integration (approval then happens from the
# admin panel). TELEGRAM_WEBHOOK_SECRET must be set in production: the webhook
# endpoint answers anonymous POSTs and its approve action grants login access,
# so without the shared secret anyone who learns the URL could approve devices.
TELEGRAM_BOT_TOKEN =config ('TELEGRAM_BOT_TOKEN',default ='')
TELEGRAM_ADMIN_CHAT_ID =config ('TELEGRAM_ADMIN_CHAT_ID',default ='')
TELEGRAM_WEBHOOK_SECRET =config ('TELEGRAM_WEBHOOK_SECRET',default ='')

# ============================================
# Device authorization policy
# ============================================
# When True (the project requirement), a device that has never been trusted
# cannot log in at all — the login is refused with a 403 and an approval
# request is sent to the admin chat. When False, the historical adaptive-MFA
# behaviour applies instead: an untrusted device may log in but must answer an
# emailed one-time code.
ENFORCE_DEVICE_AUTHORIZATION =config ('ENFORCE_DEVICE_AUTHORIZATION',default =True ,cast =bool )

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
EMAIL_HOST =config ('EMAIL_HOST',default ='')
if EMAIL_HOST :
    EMAIL_BACKEND ='django.core.mail.backends.smtp.EmailBackend'
else :
    EMAIL_BACKEND ='django.core.mail.backends.console.EmailBackend'
EMAIL_PORT =config ('EMAIL_PORT',default =587 ,cast =int )
EMAIL_HOST_USER =config ('EMAIL_HOST_USER',default ='')
EMAIL_HOST_PASSWORD =config ('EMAIL_HOST_PASSWORD',default ='')
EMAIL_USE_TLS =config ('EMAIL_USE_TLS',default =True ,cast =bool )
EMAIL_USE_SSL =config ('EMAIL_USE_SSL',default =False ,cast =bool )
DEFAULT_FROM_EMAIL =config ('DEFAULT_FROM_EMAIL',default ='SecureMed <noreply@securemed.app>')
# Used when EMAIL_BACKEND=filebased (dev/demo): real .eml files land here
EMAIL_FILE_PATH =BASE_DIR /'logs'/'emails'

# Password reset flow
# How long a reset link stays valid (seconds) — 1 hour is a good balance.
PASSWORD_RESET_TIMEOUT =config ('PASSWORD_RESET_TIMEOUT',default =3600 ,cast =int )
# Frontend base URL used inside the reset link (dev: Vite server, prod: same origin)
FRONTEND_URL =config ('FRONTEND_URL',default ='http://localhost:3000')

# ---------------------------------------------------------------- WebAuthn ----
# Relying-party identity for the FIDO2 ceremonies in apps.accounts.serializers.
#
# WEBAUTHN_RP_ID must be the registrable domain the page is served from, or a
# parent of it — the browser refuses the ceremony otherwise, and the server
# checks it again by comparing SHA-256(RP_ID) against authenticatorData.rpIdHash.
# It is NOT a URL: no scheme, no port, no path. A credential is bound to the RP
# ID it was created under, so changing this value invalidates every credential
# already enrolled; users would have to re-enroll.
WEBAUTHN_RP_ID =config ('WEBAUTHN_RP_ID',default ='')
if not WEBAUTHN_RP_ID :
    _rp_host =urlparse (FRONTEND_URL ).hostname or ''
    if not _rp_host or _rp_host =='0.0.0.0':
        _rp_host =next (
        (h .lstrip ('.')for h in ALLOWED_HOSTS if h not in ('*','0.0.0.0')),
        'localhost',
        )
    WEBAUTHN_RP_ID =_rp_host

WEBAUTHN_RP_NAME =config ('WEBAUTHN_RP_NAME',default ='SecureMed')

# Exact origins (scheme + host + port) accepted in clientDataJSON.origin. An
# allow-list, not a pattern match: this is the check that stops a signature
# collected on attacker.example from being replayed against this deployment.
WEBAUTHN_ALLOWED_ORIGINS =config (
'WEBAUTHN_ALLOWED_ORIGINS',
default ='',
cast =lambda v :[s .strip ().rstrip ('/')for s in v .split (',')if s .strip ()],
)
if not WEBAUTHN_ALLOWED_ORIGINS :
    WEBAUTHN_ALLOWED_ORIGINS =sorted ({
    o .rstrip ('/')for o in [FRONTEND_URL ,*CORS_ALLOWED_ORIGINS ,*CSRF_TRUSTED_ORIGINS ]
    if o and '*'not in o
    })

# Reject an assertion whose UV (user-verified) flag is clear. Leaving this on is
# the difference between "a biometric was presented" and "the device answered".
WEBAUTHN_REQUIRE_USER_VERIFICATION =config (
'WEBAUTHN_REQUIRE_USER_VERIFICATION',default =True ,cast =bool )

# AI_SERVICE_URL is gone. It pointed at a Node sidecar (ai-service/, port 8100)
# that no longer runs anywhere: the AI endpoints call Gemini in-process through
# apps.ai.views.get_gemini_model(), so GEMINI_API_KEY above is the only AI
# configuration left. Keeping the setting meant apps/core/health.py probed a
# closed port on every readiness check and apps/patients/views.py POSTed PHI to a
# host that was not listening.

# Logging
LOGGING ={
'version':1 ,
'disable_existing_loggers':False ,
'formatters':{
'verbose':{
'format':'{levelname} {asctime} {module} {process:d} {thread:d} {message}',
'style':'{',
},
'security':{
'format':'[SECURITY] {asctime} {levelname} {message}',
'style':'{',
},
},
'handlers':{
'console':{
'class':'logging.StreamHandler',
'formatter':'verbose',
},
'security_file':{
'class':'logging.handlers.RotatingFileHandler',
'filename':BASE_DIR /'logs'/'security.log',
'maxBytes':1024 *1024 *10 ,# 10 MB
'backupCount':5 ,
'formatter':'security',
},
},
'loggers':{
'security':{
'handlers':['security_file','console'],
'level':'INFO',
'propagate':False ,
},
'django':{
'handlers':['console'],
'level':'INFO',
'propagate':True ,
},
},
}

# Ensure runtime-writable dirs exist (cloud containers start with a clean FS)
os .makedirs (BASE_DIR /'logs',exist_ok =True )
os .makedirs (BASE_DIR /'media',exist_ok =True )
os .makedirs (BASE_DIR /'logs'/'emails',exist_ok =True )

# SPECTACULAR (API Documentation)
# The OpenAPI schema is a complete map of every endpoint, parameter and role in
# the system, i.e. free reconnaissance. /api/schema, /api/docs and /api/redoc are
# therefore registered only when this is on (default: DEBUG only).
ENABLE_API_DOCS = config('ENABLE_API_DOCS', default=DEBUG, cast=bool)

SPECTACULAR_SETTINGS ={
'TITLE':'SecureMed API',
'DESCRIPTION':'Secure Healthcare Records Management Platform with DevSecOps',
'VERSION':'2.0.0',
'SERVE_INCLUDE_SCHEMA':False ,
'COMPONENT_SPLIT_REQUEST':True ,
'SWAGGER_UI_SETTINGS': {
    'deepLinking': True,
    'persistAuthorization': True,
    'displayOperationId': True,
    'syntaxHighlight.theme': 'monokai',
    'filter': True,
},
}

# Initial superuser (for setup)
INITIAL_ADMIN_USERNAME =config ('INITIAL_ADMIN_USERNAME',default ='admin')
INITIAL_ADMIN_PASSWORD =config ('INITIAL_ADMIN_PASSWORD',default ='ChangeMe@2026!')
INITIAL_ADMIN_EMAIL =config ('INITIAL_ADMIN_EMAIL',default ='admin@securemed.app')

# Production Security Settings
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    # Exempt health checks from HTTPS redirect so internal probes don't fail with 301
    SECURE_REDIRECT_EXEMPT = [r'^health/.*']
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# ---------- Client IP resolution ----------
# Only trust X-Forwarded-For / X-Real-IP when the app really sits behind a proxy
# we control (nginx, Render, an ALB). Trusting it by default lets any client
# forge the IP recorded in audit logs, rate limits and IP blocklists.
TRUST_X_FORWARDED_FOR = config('TRUST_X_FORWARDED_FOR', default=not DEBUG, cast=bool)
# Number of trusted proxies appended to X-Forwarded-For; the client IP is the
# Nth entry from the right, so a single reverse proxy means 1.
TRUSTED_PROXY_COUNT = config('TRUSTED_PROXY_COUNT', default=1, cast=int)
# BoundJWTAuthentication binds each token to sha256(ip:user-agent). Binding to the
# IP is what makes a stolen token useless elsewhere, but it also invalidates
# tokens when a mobile client roams between networks — set this to False to bind
# to the user agent alone.
JWT_BIND_CLIENT_IP = config('JWT_BIND_CLIENT_IP', default=True, cast=bool)

# ---------- Media (PHI) access ----------
# Patient files under MEDIA_ROOT are protected health information. When Django
# serves them itself they must go through an authenticated view; set this to
# False only when an upstream proxy enforces authorisation for /media/.
PROTECT_MEDIA_FILES = config('PROTECT_MEDIA_FILES', default=True, cast=bool)
# Expose /metrics only to these networks (comma separated CIDRs / IPs) unless a
# bearer token is configured. Empty means "loopback only".
METRICS_ALLOWED_IPS = config(
    'METRICS_ALLOWED_IPS',
    default='127.0.0.1,::1',
    cast=lambda v: [s.strip() for s in v.split(',') if s.strip()],
)
METRICS_TOKEN = config('METRICS_TOKEN', default='')

REDIS_URL =config ('REDIS_URL',default ='redis://localhost:6379/0')
CELERY_BROKER_URL =config ('CELERY_BROKER_URL',default ='redis://127.0.0.1:6379/0')
CELERY_RESULT_BACKEND =config ('CELERY_RESULT_BACKEND',default ='redis://127.0.0.1:6379/0')
# Single-service / local dev mode (no Redis worker): run every .delay() task
# synchronously in-process instead of dialing a broker that isn't there —
# kombu's connect+retry loop costs ~70s per queued task otherwise.
CELERY_TASK_ALWAYS_EAGER =config ('CELERY_TASK_ALWAYS_EAGER',default =False ,cast =bool )
CELERY_TASK_EAGER_PROPAGATES =config ('CELERY_TASK_EAGER_PROPAGATES',default =False ,cast =bool )

# AI Settings
GEMINI_API_KEY =config ('GEMINI_API_KEY',default ='')

# ---------- FCM push notifications (optional) ----------
# Both must be set for push delivery to activate. FCM_SERVICE_ACCOUNT_JSON is
# either the raw JSON string of the service-account key or a path to it.
# Without these, notifications still exist in-app and by email — push is an
# additional channel, never a dependency.
FCM_PROJECT_ID =config ('FCM_PROJECT_ID',default ='')
FCM_SERVICE_ACCOUNT_JSON =config ('FCM_SERVICE_ACCOUNT_JSON',default ='')

CELERY_ACCEPT_CONTENT =['json']
CELERY_TASK_SERIALIZER ='json'
CELERY_RESULT_SERIALIZER ='json'
CELERY_TIMEZONE =TIME_ZONE
CELERY_BEAT_SCHEDULER ='django_celery_beat.schedulers:DatabaseScheduler'
CELERY_TASK_TRACK_STARTED =True 
CELERY_TASK_TIME_LIMIT =300 # 5 minutes max per task
CELERY_WORKER_PREFETCH_MULTIPLIER =1 # Fair task distribution

# Cache (Redis for sessions, rate-limiting, Celery-adjacent caching)
# Rate limiting, the JWT denylist, biometric challenges and the WAF blocklists
# all live in the cache. With a per-process LocMemCache those controls become
# per-worker — i.e. an attacker gets N times the allowance and a revoked token
# stays valid on every worker that never saw the revocation. Use Redis whenever
# it is configured (it already is, for Celery).
import sys

_TESTING = ('test' in sys.argv) or ('pytest' in sys.modules)
USE_REDIS_CACHE = config('USE_REDIS_CACHE', default=not DEBUG, cast=bool)

if USE_REDIS_CACHE and REDIS_URL and not _TESTING:
    CACHES ={
        'default':{
            'BACKEND':'django_redis.cache.RedisCache',
            'LOCATION':config ('CACHE_URL',default =REDIS_URL ),
            'KEY_PREFIX':'securemed',
            'OPTIONS':{
                'CLIENT_CLASS':'django_redis.client.DefaultClient',
                # Security controls must not fail open silently.
                'IGNORE_EXCEPTIONS':False ,
            },
        }
    }
else:
    # No Redis. In production fall back to a backend every worker can *share* —
    # DatabaseCache needs `python manage.py createcachetable` once — and keep
    # LocMemCache only for DEBUG and test runs, where one process is the whole
    # deployment. Override with CACHE_BACKEND / CACHE_LOCATION if neither fits.
    _CACHE_FALLBACK = config(
        'CACHE_BACKEND',
        default=(
            'django.core.cache.backends.locmem.LocMemCache' if (DEBUG or _TESTING)
            else 'django.core.cache.backends.db.DatabaseCache'
        ),
    )
    CACHES ={
        'default':{
            'BACKEND':_CACHE_FALLBACK ,
            'LOCATION':config (
                'CACHE_LOCATION',
                default =(
                'securemed_cache_table'if 'DatabaseCache'in _CACHE_FALLBACK
                else 'securemed-cache'
                ),
            ),
            'KEY_PREFIX':'securemed',
        }
    }

# ---------- Channels (WebSocket) layer ----------
# An in-memory layer only reaches consumers inside the same process, so group
# broadcasts (notifications, video-call signalling) are lost as soon as there is
# more than one worker.
if USE_REDIS_CACHE and REDIS_URL and not _TESTING:
    CHANNEL_LAYERS ={
        'default':{
            'BACKEND':'channels_redis.core.RedisChannelLayer',
            'CONFIG':{'hosts':[config ('CHANNEL_LAYER_URL',default =REDIS_URL )]},
        }
    }
else:
    CHANNEL_LAYERS ={
        'default':{'BACKEND':'channels.layers.InMemoryChannelLayer'},
    }

# ---------- Sentry APM Initialization ----------
SENTRY_DSN = config('SENTRY_DSN', default='')
if SENTRY_DSN and not DEBUG:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.redis import RedisIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        traces_sample_rate=1.0,
        send_default_pii=False,
    )

# ---------- Storage backends (whitenoise / S3) ----------
# Single source of truth. Django 5 expects the STORAGES dict; mixing it with the
# legacy DEFAULT_FILE_STORAGE / STATICFILES_STORAGE settings is an error.
USE_S3_STORAGE = config('USE_S3_STORAGE', default=False, cast=bool)

if USE_S3_STORAGE:
    AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID', default='')
    AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY', default='')
    AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME', default='')
    AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='us-east-1')
    AWS_S3_CUSTOM_DOMAIN = config(
        'AWS_S3_CUSTOM_DOMAIN',
        default=f'{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com',
    )
    AWS_S3_OBJECT_PARAMETERS = {'CacheControl': 'max-age=86400'}
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = None
    AWS_S3_VERIFY = True
    # Medical files must never be world-readable: serve them as signed URLs.
    AWS_QUERYSTRING_AUTH = True
    AWS_S3_ENCRYPTION = True

    STATIC_LOCATION = 'static'
    PUBLIC_MEDIA_LOCATION = 'media'
    STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/{STATIC_LOCATION}/'
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/{PUBLIC_MEDIA_LOCATION}/'

    STORAGES = {
        'default': {
            'BACKEND': 'storages.backends.s3boto3.S3Boto3Storage',
            'OPTIONS': {'location': PUBLIC_MEDIA_LOCATION},
        },
        'staticfiles': {
            'BACKEND': 'storages.backends.s3boto3.S3Boto3Storage',
            'OPTIONS': {'location': STATIC_LOCATION, 'querystring_auth': False},
        },
    }
else:
    # Encrypting at the storage layer rather than on the model is what makes this a
    # one-line change: FileField calls storage._save()/_open(), so every existing
    # FileField — MedicalFile.file, ChatMessage.attachment — is covered with no
    # migration and no change to stored names or paths. See apps.core.storage; the
    # ENCRYPT_MEDIA_AT_REST switch only governs new writes, reads detect the
    # per-file header, so existing plaintext uploads keep working either way.
    STORAGES = {
        'default': {'BACKEND': 'apps.core.storage.EncryptedFileSystemStorage'},
        'staticfiles': {
            'BACKEND': (
                'whitenoise.storage.CompressedStaticFilesStorage' if DEBUG
                else 'whitenoise.storage.CompressedManifestStaticFilesStorage'
            ),
        },
    }

# ---------- Production configuration guard ----------
# Test runs are exempt from every check below, and that exemption is not a
# convenience: pytest loads config.test_settings, which does `from .settings import *`
# with DEBUG unset, so DEBUG is False during the suite as well. CI also passes the
# placeholder ENCRYPTION_KEY deliberately. Guarding on `not DEBUG` alone therefore
# made `import config.settings` raise ImproperlyConfigured while pytest was still
# collecting, so the entire suite errored out before a single test ran. The purpose
# of this block is to stop a *deployment* booting with placeholder secrets or with
# per-process state backends; a single-process test run is neither.
if not DEBUG and not _TESTING:
    from django.core.exceptions import ImproperlyConfigured
    _insecure_defaults = {
        'SECRET_KEY': 'django-insecure-securemed-development-key-change-in-production-2026',
        'ENCRYPTION_KEY': 'securemed-field-encryption-key-32-bytes!!',
        # A deployment that never sets this ships a known admin password, and the
        # account it belongs to is a superuser — so it is exactly as serious as a
        # placeholder SECRET_KEY, and was the only one of the four documented
        # placeholders this block did not cover.
        'INITIAL_ADMIN_PASSWORD': 'ChangeMe@2026!',
    }
    for name, default_val in _insecure_defaults.items():
        if globals().get(name) == default_val:
            raise ImproperlyConfigured(
                f"{name} still uses the insecure default value in production. "
                f"Set it via environment variable before deploying."
            )

    # DB_PASSWORD only matters on the self-managed Postgres branch: with
    # DATABASE_URL set (Render/Neon) the credentials come from the URL and the
    # DB_* variables are never read.
    if not _DATABASE_URL and config('DB_ENGINE', default='') != 'sqlite':
        if config('DB_PASSWORD', default='postgres') == 'postgres':
            raise ImproperlyConfigured(
                "DB_PASSWORD still uses the default 'postgres' in production. "
                "Set it via environment variable, or use DATABASE_URL."
            )

    # Audit rows are signed with AUDIT_LOG_HMAC_KEY, falling back to SECRET_KEY so
    # that an existing deployment keeps signing instead of silently doing nothing.
    # That fallback is the wrong default for a *new* production deployment: it means
    # whoever leaks SECRET_KEY can also forge audit history, and audit history is
    # the last thing that still holds after every other control has failed.
    #
    # Refuse to boot without a dedicated key. A deployment whose rows were already
    # signed with SECRET_KEY cannot simply switch — a new key makes every existing
    # signature unverifiable — so it opts out explicitly and keeps that decision
    # visible in its environment instead of inheriting it by silence.
    if not AUDIT_LOG_HMAC_KEY and not config(
        'AUDIT_LOG_ALLOW_SECRET_KEY_FALLBACK', default=False, cast=bool
    ):
        raise ImproperlyConfigured(
            "AUDIT_LOG_HMAC_KEY is not set, so audit rows would be signed with "
            "SECRET_KEY and anyone holding it could forge audit history. Generate "
            "a dedicated key (e.g. 'python -c \"import secrets;"
            "print(secrets.token_urlsafe(64))\"') and set AUDIT_LOG_HMAC_KEY. "
            "An existing deployment whose rows are already signed with SECRET_KEY "
            "must keep the fallback — rotating invalidates every past signature — "
            "and declares that with AUDIT_LOG_ALLOW_SECRET_KEY_FALLBACK=1."
        )

    # Shared-state backends must actually be shared. Rate limits, the JWT
    # denylist, biometric challenges and the WAF blocklists all live in the
    # cache; on a per-process LocMemCache each worker enforces its own copy, so
    # an attacker gets N times every allowance and a revoked refresh token keeps
    # working on every worker that never saw the revocation. That is a silent
    # failure, which is the worst kind — refuse to boot instead.
    _cache_backend = CACHES.get('default', {}).get('BACKEND', '')
    if 'locmem' in _cache_backend.lower():
        raise ImproperlyConfigured(
            "CACHES['default'] is LocMemCache while DEBUG=False. Rate limiting, "
            "the JWT denylist and the WAF blocklists would be per-worker and "
            "therefore unenforceable. Set REDIS_URL (recommended), or set "
            "CACHE_BACKEND=django.core.cache.backends.db.DatabaseCache and run "
            "'python manage.py createcachetable' once."
        )
    if 'InMemoryChannelLayer' in CHANNEL_LAYERS.get('default', {}).get('BACKEND', ''):
        if not config('ALLOW_IN_MEMORY_CHANNELS', default=False, cast=bool):
            raise ImproperlyConfigured(
                "CHANNEL_LAYERS['default'] is InMemoryChannelLayer while DEBUG=False. "
                "WebSocket group broadcasts would only reach consumers inside the same "
                "process. Set REDIS_URL so channels_redis is used. If this is a "
                "single-process deployment (like a free tier), set ALLOW_IN_MEMORY_CHANNELS=1."
            )

    # An operator who sets JWT_ALGORITHM=RS256 has decided that access tokens must
    # be verifiable without the signing secret. Falling back to HS256 because a PEM
    # was missing would hand that property back without saying so, and the tokens
    # would keep working, so nothing would ever surface it.
    if _JWT_RS256_REQUESTED and SIMPLE_JWT['ALGORITHM'] != 'RS256':
        raise ImproperlyConfigured(
            "JWT_ALGORITHM=RS256 was requested but the keypair is unusable "
            f"({_JWT_RS256_ERROR or 'no PEM found'}). Generate it with "
            "'python scripts/generate_certificates.py', or point "
            "JWT_PRIVATE_KEY_PATH / JWT_PUBLIC_KEY_PATH at existing PEM files. "
            "Unset JWT_ALGORITHM to use HS256 with SECRET_KEY instead."
        )

    # ---------- Well-known seed passwords ----------
    # backend/scripts/seed_data.py creates 10 demo users with passwords that are
    # literally in the repo (admin@securemed.app / Admin@2026!, doctor.* /
    # Doctor@2026!, etc.). SEED_DEMO_DATA is the documented opt-in for that
    # path; allowing it on a deployment that real users can reach would leave
    # every demo account as a published login. Refuse the combination rather
    # than one of them, because the meaningful mistake is enabling the seed
    # outside of a dev environment, not choosing a particular password.
    if config('SEED_DEMO_DATA', default='0').lower() in ('1', 'true', 'yes', 'on'):
        raise ImproperlyConfigured(
            "SEED_DEMO_DATA is enabled in production. "
            "backend/scripts/seed_data.py will create 10 accounts whose passwords "
            "are committed to the repo (admin@securemed.app / Admin@2026!, "
            "doctor.* / Doctor@2026!, etc.). Set SEED_DEMO_DATA=0 before deploying."
        )
