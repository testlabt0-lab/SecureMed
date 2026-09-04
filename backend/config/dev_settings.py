"""
Dev settings for running SecureMed locally without PostgreSQL.
Uses SQLite for easy testing.
"""
import os 
from datetime import timedelta 
from .settings import *# Comment_437

# Comment_438
DATABASES ={
'default':{
'ENGINE':'django.db.backends.sqlite3',
'NAME':BASE_DIR /'db.sqlite3',
}
}

# Comment_439
for db in DATABASES .values ():
    db .get ('OPTIONS',{}).pop ('sslmode',None )
    db .get ('OPTIONS',{}).pop ('sslrootcert',None )
    db .get ('OPTIONS',{}).pop ('sslcert',None )
    db .get ('OPTIONS',{}).pop ('sslkey',None )

    # Comment_440
DEBUG =True 
SECRET_KEY ='dev-secret-key-not-for-production'
ALLOWED_HOSTS =['*']

# Comment_441
SECURE_SSL_REDIRECT =False 
SESSION_COOKIE_SECURE =False 
CSRF_COOKIE_SECURE =False 
SECURE_HSTS_SECONDS =0 
SECURE_HSTS_INCLUDE_SUBDOMAINS =False 
SECURE_HSTS_PRELOAD =False 
SECURE_PROXY_SSL_HEADER =None 

# Comment_442
SIMPLE_JWT ={
'ACCESS_TOKEN_LIFETIME':timedelta (minutes =15 ),
'REFRESH_TOKEN_LIFETIME':timedelta (days =1 ),
'ROTATE_REFRESH_TOKENS':True ,
'BLACKLIST_AFTER_ROTATION':True ,
'ALGORITHM':'HS256',
'SIGNING_KEY':SECRET_KEY ,
'AUTH_HEADER_TYPES':('Bearer',),
'USER_ID_FIELD':'id',
'USER_ID_CLAIM':'user_id',
'TOKEN_TYPE_CLAIM':'token_type',
'JTI_CLAIM':'jti',
}

# Comment_443
INSTALLED_APPS =[app for app in INSTALLED_APPS if app !='django_ratelimit']
MIDDLEWARE =[m for m in MIDDLEWARE if 'ratelimit'not in m .lower ()]

# Comment_444
CACHES ={
'default':{
'BACKEND':'django.core.cache.backends.locmem.LocMemCache',
'LOCATION':'dev',
}
}

# Comment_445
MOCK_SERVICES =os .environ .get ('MOCK_SERVICES','true').lower ()=='true'
if MOCK_SERVICES :
    from mock_services .config import MOCK_SERVICES as _MS # Comment_446
    # Comment_447
    import mock_services 
    mock_service =mock_services .patch_ai_service ()

    # Comment_448
    CACHES ={
    'default':{
    'BACKEND':'django.core.cache.backends.locmem.LocMemCache',
    'LOCATION':'dev-mock',
    }
    }

    # Comment_449
    try :
        import redis as _redis 
        _redis_client =_redis .from_url (os .environ .get ('REDIS_URL','redis://localhost:6379/0'),decode_responses =True )
        _redis_client .ping ()
    except Exception :
        import mock_services as _ms 
        from unittest .mock import MagicMock 
        _redis_client =MagicMock ()
        _redis_client .get .return_value =None 
        _redis_client .set .return_value =True 
        _redis_client .exists .return_value =False 
        _redis_client .flushdb .return_value =None 
        _redis_client .ping .return_value =True 

        # Comment_450
    EMAIL_BACKEND ='django.core.mail.backends.console.EmailBackend'

    # Comment_451
    # Comment_452
    # Comment_453
EMAIL_BACKEND ='django.core.mail.backends.filebased.EmailBackend'
EMAIL_FILE_PATH =BASE_DIR /'logs'/'emails'
