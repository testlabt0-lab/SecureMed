import os
import asyncio
import django
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ["DEBUG"] = "False"
os.environ["ENCRYPTION_KEY"] = "12345678901234567890123456789012"
os.environ["INITIAL_ADMIN_PASSWORD"] = "123"
os.environ["AUDIT_LOG_HMAC_KEY"] = "123"
os.environ["ALLOWED_HOSTS"] = "*"
django.setup()

from django.core.handlers.asgi import ASGIHandler
from asgiref.testing import ApplicationCommunicator

async def test():
    application = ASGIHandler()
    scope = {
        'type': 'http',
        'http_version': '1.1',
        'method': 'GET',
        'path': '/health/live/',
        'raw_path': b'/health/live/',
        'query_string': b'',
        'headers': [
            (b'host', b'100.64.0.2:8080'),
            (b'connection', b'close')
        ],
        'client': ('100.64.0.2', 36045),
        'server': ('0.0.0.0', 8080),
    }
    communicator = ApplicationCommunicator(application, scope)
    await communicator.send_input({'type': 'http.request', 'body': b''})
    
    # Get the response start (status code & headers)
    response_start = await communicator.receive_output(10)
    print(f"Status code: {response_start['status']}")
    for k, v in response_start.get('headers', []):
        print(f"{k.decode()}: {v.decode()}")

asyncio.run(test())
