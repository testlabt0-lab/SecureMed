"""
Django settings for SecureMed platform.
Implements all 6 security requirements from the doctor's specifications.
"""
import os 
from datetime import timedelta 
from pathlib import Path 
from decouple import config 

BASE_DIR =Path (__file__ ).resolve ().parent .parent 

# Comment_454
SECRET_KEY =config (
'SECRET_KEY',
default ='django-insecure-securemed-development-key-change-in-production-2026',
)

# Comment_455
DEBUG =config ('DEBUG',default =False ,cast =bool )
ALLOWED_HOSTS =config (
'ALLOWED_HOSTS',
default ='localhost,127.0.0.1,0.0.0.0',
cast =lambda v :[s .strip ()for s in v .split (',')]
)

# Comment_456
INSTALLED_APPS =[
'unfold', # Must be before django.contrib.admin
'daphne',
'django.contrib.admin',
'django.contrib.auth',
'django.contrib.contenttypes',
'django.contrib.sessions',
'django.contrib.messages',
'django.contrib.staticfiles',
# Comment_457
'rest_framework',
'rest_framework_simplejwt',
'rest_framework_simplejwt.token_blacklist',
'corsheaders',
'django_extensions',
'drf_spectacular',
'django_filters',
# Comment_458
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
# Comment_459
'django_celery_beat',
'django_celery_results',

# Comment_460
'channels',
]

UNFOLD = {
    "SITE_TITLE": "SecureMed Admin",
    "SITE_HEADER": "SecureMed Admin",
    "SITE_URL": "/",
    "DASHBOARD_CALLBACK": "apps.analytics.admin_dashboard.dashboard_callback",
    "COLORS": {
        "primary": {
            "50": "236 253 245",
            "100": "209 250 229",
            "200": "167 243 208",
            "300": "110 231 183",
            "400": "52 211 153",
            "500": "16 185 129",
            "600": "5 150 105",
            "700": "4 120 87",
            "800": "6 95 70",
            "900": "6 78 59",
            "950": "2 44 34",
        },
    },
}

MIDDLEWARE =[
# Comment_461
'django.middleware.security.SecurityMiddleware',
# Comment_462
# Comment_463
'django.middleware.gzip.GZipMiddleware',
'whitenoise.middleware.WhiteNoiseMiddleware',
'corsheaders.middleware.CorsMiddleware',
# Comment_464
'apps.security.middleware.WAFMiddleware',
'django.contrib.sessions.middleware.SessionMiddleware',
'django.middleware.common.CommonMiddleware',
# Comment_465
'django.middleware.csrf.CsrfViewMiddleware',
'django.contrib.auth.middleware.AuthenticationMiddleware',
'django.contrib.messages.middleware.MessageMiddleware',
'django.middleware.clickjacking.XFrameOptionsMiddleware',
# Comment_466
'apps.audit.middleware.AuditLogMiddleware',
# Comment_467
'apps.security.middleware.RateLimitMiddleware',
# Comment_468
'apps.security.middleware.SessionSecurityMiddleware',
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

CHANNEL_LAYERS ={
"default":{
"BACKEND":"channels_redis.core.RedisChannelLayer",
"CONFIG":{
"hosts":[(config ('REDIS_HOST',default ='127.0.0.1'),config ('REDIS_PORT',default =6379 ,cast =int ))],
},
},
}

# Comment_469
# Comment_470
# Comment_471
# Comment_472
_DB_SSL_OPTIONS ={'sslmode':config ('DB_SSLMODE',default ='require')}
if config ('DB_SSL_CLIENT_CERTS',default =False ,cast =bool ):
# Comment_473
    _DB_SSL_OPTIONS .update ({
    'sslrootcert':os .path .join (BASE_DIR ,'certs','ca.pem'),
    'sslcert':os .path .join (BASE_DIR ,'certs','client.pem'),
    'sslkey':os .path .join (BASE_DIR ,'certs','client-key.pem'),
    })

    # Comment_474
    # Comment_475
    # Comment_476
    # Comment_477
    # Comment_478
    # Comment_479
    # Comment_480
    # Comment_481
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

    # Comment_482
AUTH_PASSWORD_VALIDATORS =[
{'NAME':'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
{'NAME':'django.contrib.auth.password_validation.MinimumLengthValidator',
'OPTIONS':{'min_length':12 }},
{'NAME':'django.contrib.auth.password_validation.CommonPasswordValidator'},
{'NAME':'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Comment_483
AUTH_USER_MODEL ='accounts.User'

UNFOLD = {
    "SITE_TITLE": "SecureMed Admin",
    "SITE_HEADER": "SecureMed Platform",
    "SITE_URL": "/",
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
    }
}

# Comment_484
LANGUAGE_CODE ='ar'
TIME_ZONE ='Asia/Aden'
USE_I18N =True 
USE_TZ =True 

# Comment_485
# Comment_486
# Comment_487
STATIC_URL ='/static/'
STATIC_ROOT =BASE_DIR /'staticfiles'
STATICFILES_STORAGE ='whitenoise.storage.CompressedStaticFilesStorage'

# Comment_488
FRONTEND_DIST =Path (config ('FRONTEND_DIST',default =str (BASE_DIR .parent /'frontend'/'dist')))
TEMPLATES [0 ]['DIRS']=[BASE_DIR /'templates',FRONTEND_DIST ]
STATICFILES_DIRS =[str (FRONTEND_DIST )]if FRONTEND_DIST .exists ()else []

# Comment_489
MEDIA_URL ='/media/'
MEDIA_ROOT =BASE_DIR /'media'

# ---------- AWS S3 Cloud Storage ----------
USE_S3_STORAGE = config('USE_S3_STORAGE', default=False, cast=bool)

if USE_S3_STORAGE:
    AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID', default='')
    AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY', default='')
    AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME', default='')
    AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='us-east-1')
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = None
    AWS_S3_VERIFY = True
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'


# Comment_490
DATA_UPLOAD_MAX_MEMORY_SIZE =20 *1024 *1024 # Comment_491
FILE_UPLOAD_MAX_MEMORY_SIZE =20 *1024 *1024 # Comment_492
FILE_UPLOAD_PERMISSIONS =0o644 

# Comment_493
DEFAULT_AUTO_FIELD ='django.db.models.BigAutoField'

# Comment_494
# Comment_495
# Comment_496

# Comment_497
SESSION_COOKIE_SECURE =True 
SESSION_COOKIE_HTTPONLY =True 
SESSION_COOKIE_SAMESITE ='Strict'
CSRF_COOKIE_SECURE =True 
CSRF_COOKIE_HTTPONLY =True 
CSRF_COOKIE_SAMESITE ='Strict'
SESSION_COOKIE_AGE =3600 # Comment_498
SESSION_EXPIRE_AT_BROWSER_CLOSE =True 

# Comment_499
SECURE_SSL_REDIRECT =config ('SECURE_SSL_REDIRECT',default =not DEBUG ,cast =bool )
SECURE_HSTS_SECONDS =config ('SECURE_HSTS_SECONDS',default =31536000 ,cast =int )# Comment_500
SECURE_HSTS_INCLUDE_SUBDOMAINS =True 
SECURE_HSTS_PRELOAD =True 
SECURE_PROXY_SSL_HEADER =('HTTP_X_FORWARDED_PROTO','https')
SECURE_CONTENT_TYPE_NOSNIFF =True 
SECURE_BROWSER_XSS_FILTER =True 
SECURE_REFERRER_POLICY ='same-origin'
X_FRAME_OPTIONS ='DENY'

# Comment_501
CORS_ALLOWED_ORIGINS =config (
'CORS_ALLOWED_ORIGINS',
default ='http://localhost:3000,http://127.0.0.1:3000',
cast =lambda v :[s .strip ()for s in v .split (',')]
)
CORS_ALLOW_CREDENTIALS =True 

# Comment_502
# Comment_503
_CSRF_ENV =config ('CSRF_TRUSTED_ORIGINS',default ='').strip ()
if _CSRF_ENV :
    CSRF_TRUSTED_ORIGINS =[s .strip ()for s in _CSRF_ENV .split (',')if s .strip ()]
else :
    CSRF_TRUSTED_ORIGINS =[
    'https://'+('*'+h if h .startswith ('.')else h )
    for h in ALLOWED_HOSTS if h not in ('*',)
    ]

    # Comment_504
    # Comment_505
    # Comment_506
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

# Comment_507
# Comment_508
_JWT_PRIV =BASE_DIR /'certs'/'jwt_private.pem'
_JWT_PUB =BASE_DIR /'certs'/'jwt_public.pem'
_JWT_ALGO =config ('JWT_ALGORITHM',default ='RS256'if _JWT_PRIV .exists ()else 'HS256')

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
if _JWT_ALGO =='RS256'and _JWT_PRIV .exists ()and _JWT_PUB .exists ():
    SIMPLE_JWT ={
    **_JWT_BASE ,
    'ALGORITHM':'RS256',# Comment_509
    'SIGNING_KEY':config ('JWT_PRIVATE_KEY_PATH',default =str (_JWT_PRIV )),
    'VERIFYING_KEY':config ('JWT_PUBLIC_KEY_PATH',default =str (_JWT_PUB )),
    }
else :
    SIMPLE_JWT ={
    **_JWT_BASE ,
    'ALGORITHM':'HS256',
    'SIGNING_KEY':config ('JWT_SIGNING_KEY',default =SECRET_KEY ),
    }

    # Comment_510
    # Comment_511
    # Comment_512
ENCRYPTION_KEY =config (
'ENCRYPTION_KEY',
default ='securemed-field-encryption-key-32-bytes!!',# Comment_513
)
USE_FIELD_ENCRYPTION =True 

# Comment_514
BIOMETRIC_SETTINGS ={
'CHALLENGE_TTL_SECONDS':60 ,
'MAX_FAILED_ATTEMPTS':5 ,
'LOCKOUT_DURATION_MINUTES':30 ,
'HASH_ALGORITHM':'sha256',
}

# Comment_315
ADAPTIVE_MFA_ENABLED = True

# Comment_516
# Comment_517
BACKUP_DIR =Path (config ('BACKUP_DIR',default =str (BASE_DIR /'backups')))
BACKUP_KEEP_COUNT =config ('BACKUP_KEEP_COUNT',default =14 ,cast =int )

# Comment_518
# Comment_519
# Comment_520
# Comment_521
# Comment_522

# Comment_523
# Comment_524
# Comment_525
# Comment_526
# Comment_527

# Comment_528
# Comment_529
# Comment_530
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
# Comment_531
EMAIL_FILE_PATH =BASE_DIR /'logs'/'emails'

# Comment_532
# Comment_533
PASSWORD_RESET_TIMEOUT =config ('PASSWORD_RESET_TIMEOUT',default =3600 ,cast =int )
# Comment_534
FRONTEND_URL =config ('FRONTEND_URL',default ='http://localhost:3000')

# Comment_535
AI_SERVICE_URL =config ('AI_SERVICE_URL',default ='http://127.0.0.1:8100')

# Comment_536
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
'maxBytes':1024 *1024 *10 ,# Comment_537
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

# Comment_538
os .makedirs (BASE_DIR /'logs',exist_ok =True )
os .makedirs (BASE_DIR /'media',exist_ok =True )
os .makedirs (BASE_DIR /'logs'/'emails',exist_ok =True )

# Comment_539
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

# Comment_540
INITIAL_ADMIN_USERNAME =config ('INITIAL_ADMIN_USERNAME',default ='admin')
INITIAL_ADMIN_PASSWORD =config ('INITIAL_ADMIN_PASSWORD',default ='ChangeMe@2026!')
INITIAL_ADMIN_EMAIL =config ('INITIAL_ADMIN_EMAIL',default ='admin@securemed.app')

# Production Security Settings
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    # Use WhiteNoise for static files
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

REDIS_URL =config ('REDIS_URL',default ='redis://localhost:6379/0')

CELERY_BROKER_URL =config ('CELERY_BROKER_URL',default ='redis://127.0.0.1:6379/0')
CELERY_RESULT_BACKEND =config ('CELERY_RESULT_BACKEND',default ='redis://127.0.0.1:6379/0')

# Comment_544
GEMINI_API_KEY =config ('GEMINI_API_KEY',default ='')

CELERY_ACCEPT_CONTENT =['json']
CELERY_TASK_SERIALIZER ='json'
CELERY_RESULT_SERIALIZER ='json'
CELERY_TIMEZONE ='Asia/Riyadh'
CELERY_BEAT_SCHEDULER ='django_celery_beat.schedulers:DatabaseScheduler'
CELERY_TASK_TRACK_STARTED =True 
CELERY_TASK_TIME_LIMIT =300 # Comment_545
CELERY_WORKER_PREFETCH_MULTIPLIER =1 # Comment_546

# Comment_547
import sys 
if 'pytest'in sys .modules or os .environ .get ('TESTING')=='True'or 'test'in sys .argv :
    CACHES ={
    'default':{
    'BACKEND':'django.core.cache.backends.locmem.LocMemCache',
    'LOCATION':'securemed-test-cache',
    }
    }
else :
    CACHES ={
    'default':{
    'BACKEND':'django_redis.cache.RedisCache',
    'LOCATION':REDIS_URL ,
    'OPTIONS':{
    'CLIENT_CLASS':'django_redis.client.DefaultClient',
    'SOCKET_CONNECT_TIMEOUT':5 ,
    'SOCKET_TIMEOUT':5 ,
    'IGNORE_EXCEPTIONS':True ,# Comment_548
    },
    'KEY_PREFIX':'securemed',
    'TIMEOUT':300 ,# Comment_549
    }
    }
