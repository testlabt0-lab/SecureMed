"""
Dev settings for running SecureMed locally without PostgreSQL.
Uses SQLite for easy testing.
"""
import os 
from datetime import timedelta 
from .settings import *# noqa

# Use SQLite for dev (no PostgreSQL required)
DATABASES ={
'default':{
'ENGINE':'django.db.backends.sqlite3',
'NAME':BASE_DIR /'db.sqlite3',
}
}

# Disable SSL for dev
for db in DATABASES .values ():
    db .get ('OPTIONS',{}).pop ('sslmode',None )
    db .get ('OPTIONS',{}).pop ('sslrootcert',None )
    db .get ('OPTIONS',{}).pop ('sslcert',None )
    db .get ('OPTIONS',{}).pop ('sslkey',None )

    # Dev settings
DEBUG =True 
SECRET_KEY ='dev-secret-key-not-for-production'
ALLOWED_HOSTS =['*']

# Disable SSL redirect for dev
SECURE_SSL_REDIRECT =False 
SESSION_COOKIE_SECURE =False 
CSRF_COOKIE_SECURE =False 
SECURE_HSTS_SECONDS =0 
SECURE_HSTS_INCLUDE_SUBDOMAINS =False 
SECURE_HSTS_PRELOAD =False 
SECURE_PROXY_SSL_HEADER =None 

# Use HMAC for JWT in dev (no PEM file needed)
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

# Rate limiting is now enabled in dev as well to ensure security testing

# Use in-memory cache
CACHES ={
'default':{
'BACKEND':'django.core.cache.backends.locmem.LocMemCache',
'LOCATION':'securemed-dev-cache',
}
}

# The MOCK_SERVICES block that used to live here is gone. It imported
# mock_services.config, which at import time replaced AIAssistantAskView.post and
# AIAssistantHealthView.get with stubs. Three problems, and it defaulted to ON in
# development:
#   * the stub referenced an unimported `Response`, so every POST to
#     /api/v1/ai/ask/ answered 500 NameError;
#   * /api/v1/ai/health/ reported "Mock AI Service / healthy" regardless;
#   * the stubs skipped _require_module() and anonymize_patient_data(), so a dev
#     working against real records lost both the basin gate and PHI masking.
# It existed because there was no AI service to talk to locally. There is no
# service to miss now: apps.ai.views calls Gemini in-process and, with no
# GEMINI_API_KEY set, answers 200 with an "AI is not configured" message. The dev
# experience the mock was for is the default behaviour.

# Mail goes to logs/emails/ as .log files. The mock block also set
# EMAIL_BACKEND='...console.EmailBackend' a few lines above this, which this
# assignment then overwrote unconditionally — so the console backend never applied
# and reading either line alone gave the wrong answer about where dev mail lands.
EMAIL_BACKEND ='django.core.mail.backends.filebased.EmailBackend'
EMAIL_FILE_PATH =BASE_DIR /'logs'/'emails'

# Run Celery tasks synchronously in dev to avoid Redis dependency
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_STORE_EAGER_RESULT = True
# Disable async audit logging to avoid broker connection attempts
AUDIT_LOG_ASYNC = False
