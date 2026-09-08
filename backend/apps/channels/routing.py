from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(
        r'ws/channel_chat/(?P<channel_id>[\w-]+)/$',
        consumers.ChannelChatConsumer.as_asgi(),
    ),
]
