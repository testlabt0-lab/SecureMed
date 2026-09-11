import os
import django
from django.conf import settings
from asgiref.testing import ApplicationCommunicator
from config.asgi import application
import asyncio

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ["DEBUG"] = "False"
os.environ["ALLOWED_HOSTS"] = "*"

async def run_test():
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "path": "/health/live/",
        "raw_path": b"/health/live/",
        "query_string": b"",
        "headers": [
            (b"host", b"100.64.0.2:8080"),
            (b"user-agent", b"Railway-Healthcheck"),
        ],
        "client": ["100.64.0.2", 56365],
        "server": ["100.64.0.2", 8080],
    }

    communicator = ApplicationCommunicator(application, scope)
    await communicator.send_input({"type": "http.request", "body": b""})

    response_start = await communicator.receive_output(2)
    print("Response Start:", response_start)
    
    if response_start["type"] == "http.response.start":
        print(f"Status: {response_start['status']}")
        for name, value in response_start.get("headers", []):
            print(f"{name.decode('utf-8')}: {value.decode('utf-8')}")

asyncio.run(run_test())
