"""
ASGI config for SecureMed platform.

Supports both HTTP (Django) and WebSocket (Channels) connections.
Used by Daphne or Uvicorn for production deployments with WebSocket support.
"""
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
from pathlib import Path

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Initialize Django application
django_asgi_app = get_asgi_application()

# Import WebSocket routing after Django setup
from apps.websocket.routing import websocket_urlpatterns


class AllowedHostsOriginValidatorWithWS(AllowedHostsOriginValidator):
    """
    Custom validator that allows WebSocket connections from allowed hosts
    """
    pass


# ASGI application with WebSocket support
application = ProtocolTypeRouter({
    # HTTP requests handled by Django
    "http": django_asgi_app,
    
    # WebSocket requests handled by Channels
    "websocket": AllowedHostsOriginValidatorWithWS(
        AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        )
    ),
})
