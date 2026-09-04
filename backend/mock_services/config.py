"""
Mock services configuration for SecureMed.

Activate by setting MOCK_SERVICES=true in .env or environment.
This simulates external services (AI, Redis, etc.) for development and testing.
"""
import os 

MOCK_SERVICES =os .environ .get ('MOCK_SERVICES','false').lower ()=='true'

if MOCK_SERVICES :
# Comment_574
    import mock_services 
    mock_service =mock_services .patch_ai_service ()

    # Comment_575
    try :
        import redis 
        redis_client =redis .from_url (os .environ .get ('REDIS_URL','redis://localhost:6379/0'),decode_responses =True )
        # Comment_576
        redis_client .ping ()
    except Exception :
    # Comment_577
        import mock_services as ms 
        from unittest .mock import MagicMock 
        redis_client =MagicMock ()
        # Comment_578
        redis_client .get .return_value =None 
        redis_client .set .return_value =True 
        redis_client .exists .return_value =False 
        redis_client .flushdb .return_value =None 
        redis_client .close .return_value =None 
        redis_client .ping .return_value =True 

        # Comment_579
    import django 
    from django_redis import get_redis_connection 
    # Comment_580