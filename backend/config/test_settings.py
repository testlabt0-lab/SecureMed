# Test settings for SecureMed
# Uses SQLite for fast test execution, disables SSL for dev
import os 
from datetime import timedelta 
from .settings import *# noqa

# Use SQLite for tests (faster, no PostgreSQL required)
SECURE_SSL_REDIRECT = False
DATABASES ={
'default':{
'ENGINE':'django.db.backends.sqlite3',
'NAME':':memory:',
}
}

# The ZTNA consent firewall answers 403 to every /api/ request that does not
# carry an approved device fingerprint, which is correct in production but
# means DRF tests can never reach a view. No test exercises the consent wall
# itself, so it is lifted here; ZTNA flows are covered by the views it calls.
MIDDLEWARE =[
mw for mw in MIDDLEWARE if 'ZeroTrustConsentFirewallMiddleware' not in mw
]

# Disable SSL for tests
for db in DATABASES .values ():
    db .get ('OPTIONS',{}).pop ('sslmode',None )
    db .get ('OPTIONS',{}).pop ('sslrootcert',None )
    db .get ('OPTIONS',{}).pop ('sslcert',None )
    db .get ('OPTIONS',{}).pop ('sslkey',None )

# The MOCK_SERVICES block that used to live here is gone — see the note in
# config/dev_settings.py. Under test it was doubly wrong: the AI views are
# exercised against their real code by patching apps.ai.views.get_gemini_model
# (tests/test_phase6_deployment.py), and monkeypatching the view methods instead
# would have made those tests assert the stub's behaviour, not the application's.
CACHES ={
'default':{
'BACKEND':'django.core.cache.backends.locmem.LocMemCache',
'LOCATION':'test-memory-cache',
}
}

REST_FRAMEWORK ['DEFAULT_THROTTLE_CLASSES']=[]
REST_FRAMEWORK ['DEFAULT_THROTTLE_RATES']={
'anon':'10000/hour',
'user':'10000/hour',
'login':'10000/minute',
'biometric':'10000/minute',
'password_reset':'10000/hour',
}

# Use MD5 hasher for faster testing
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable Celery broker for tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
# STORE_EAGER_RESULT = True made every eager task write its result to the
# configured backend — redis://127.0.0.1:6379 — which is not running under test.
# `.delay()` then raised *after* the task had already done its work, so callers
# with a synchronous fallback (apps.audit.utils.log_security_event) wrote the row
# a second time. Tests never read task results, so keep them out of the backend.
CELERY_TASK_STORE_EAGER_RESULT = False
CELERY_BROKER_URL = 'memory://'
CELERY_RESULT_BACKEND = 'cache+memory://'

# Neutralise live credentials picked up from a developer's local .env. python-decouple
# reads that file at import time, so a .env carrying a real TELEGRAM_BOT_TOKEN /
# BACKUP_SEND_TO_TELEGRAM pair would otherwise leak into the suite: backup tests would
# POST fake archives to a live Telegram chat, and any test asserting a single delivery
# channel would see BOTH. Tests that exercise a channel opt into it explicitly.
BACKUP_SEND_TO_TELEGRAM = False
TELEGRAM_BOT_TOKEN = ''
TELEGRAM_ADMIN_CHAT_ID = ''
BACKUP_OFFSITE_ENABLED = False
BACKUP_OFFSITE_ACCESS_KEY_ID = ''
BACKUP_OFFSITE_SECRET_ACCESS_KEY = ''

# Never reach a real Gemini endpoint from a test run.
GEMINI_API_KEY = ''

# A fixed HMAC key makes the audit chain deterministic and independent of any
# value a local .env happens to define.
AUDIT_LOG_HMAC_KEY = 'securemed-test-audit-hmac-key'
