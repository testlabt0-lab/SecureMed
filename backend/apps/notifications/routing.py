from django.urls import re_path
from . import consumers as notif_consumers
from apps.appointments import consumers as rtc_consumers

websocket_urlpatterns = [
    re_path(r'ws/notifications/$', notif_consumers.NotificationConsumer.as_asgi()),
    re_path(r'ws/webrtc/(?P<room_name>\w+)/$', rtc_consumers.VideoCallConsumer.as_asgi()),
]
