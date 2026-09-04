# Comment_550
# Comment_551
import os 
from datetime import timedelta 
from .settings import *# Comment_552

# Comment_553
DATABASES ={
'default':{
'ENGINE':'django.db.backends.sqlite3',
'NAME':':memory:',
}
}

# Comment_554
for db in DATABASES .values ():
    db .get ('OPTIONS',{}).pop ('sslmode',None )
    db .get ('OPTIONS',{}).pop ('sslrootcert',None )
    db .get ('OPTIONS',{}).pop ('sslcert',None )
    db .get ('OPTIONS',{}).pop ('sslkey',None )

    # Comment_555
CACHES ={
'default':{
'BACKEND':'django.core.cache.backends.locmem.LocMemCache',
'LOCATION':'test-memory-cache',
}
}

# Comment_556
MOCK_SERVICES =os .environ .get ('MOCK_SERVICES','false').lower ()=='true'
if MOCK_SERVICES :
# Comment_557
    from mock_services .config import MOCK_SERVICES as _MS # Comment_558
    # Comment_559
    import mock_services 
    mock_service =mock_services .patch_ai_service ()

    # Comment_560
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
        # Comment_561
REST_FRAMEWORK ['DEFAULT_THROTTLE_CLASSES']=[]
REST_FRAMEWORK ['DEFAULT_THROTTLE_RATES']={
'anon':'10000/hour',
'user':'10000/hour',
'login':'10000/minute',
'biometric':'10000/minute',
'password_reset':'10000/hour',
}
