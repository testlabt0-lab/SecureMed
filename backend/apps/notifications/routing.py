from django.urls import re_path

from . import consumers as notif_consumers

websocket_urlpatterns = [
    re_path(r'ws/notifications/$', notif_consumers.NotificationConsumer.as_asgi()),
]

# `ws/webrtc/<room>/` used to be routed here to a second copy of
# VideoCallConsumer in apps/appointments/consumers.py. That copy carried the
# comment "In a real app, verify if the user has access to this room" and did not,
# so any account that guessed a room name joined the call and received the live
# SDP/ICE exchange of somebody else's consultation. It was also unreachable from
# any client — nothing in the SPA or the Android app opened that path. The single
# authorised signalling consumer now lives in apps/telemedicine/routing.py at
# `ws/video_call/<room>/`.
