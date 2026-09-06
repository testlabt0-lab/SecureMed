from django.urls import re_path

from . import consumers

# `\w+` could never match a real room: Consultation.room_id defaults to
# `uuid.uuid4`, whose string form contains hyphens, and `\w` does not match `-`.
# Every join attempt fell through the URLRouter and was closed as "no route
# found", which looked like a client bug.
websocket_urlpatterns = [
    re_path(r'ws/video_call/(?P<room_name>[\w-]+)/$', consumers.VideoCallConsumer.as_asgi()),
]
