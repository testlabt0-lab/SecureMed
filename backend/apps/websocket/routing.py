"""
WebSocket routing for SecureMed
"""
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/notifications/$', consumers.NotificationConsumer.as_asgi()),
    re_path(r'ws/updates/(?P<room_name>\w+)/$', consumers.UpdateConsumer.as_asgi()),
]
