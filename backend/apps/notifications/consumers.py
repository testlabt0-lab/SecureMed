"""Per-user notification socket.

Group name is ``user_<uuid>``; ``apps.notifications.utils`` sends into it whenever a
notification row is created, so the client does not have to poll.
"""
import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger('notifications')

# Application close codes. 4001 is the convention for "authenticate and retry";
# the client distinguishes it from a transport drop so it does not reconnect in a
# loop with a credential the server has already refused.
CLOSE_UNAUTHENTICATED = 4001


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        self.room_group_name = None

        if not self.user or not self.user.is_authenticated:
            # This branch used to `accept()` the socket and then do nothing: no
            # group was joined, so the client held an open, unauthenticated
            # connection that would never deliver a single notification. Closing
            # before the handshake completes is both the honest answer and the one
            # the client can act on.
            await self.close(code=CLOSE_UNAUTHENTICATED)
            return

        self.room_group_name = f'user_{self.user.id}'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        # A browser that offered Sec-WebSocket-Protocol requires the server to echo
        # one of the offered values, otherwise it fails the handshake client-side.
        await self.accept(subprotocol=self.scope.get('ws_subprotocol'))

    async def disconnect(self, close_code):
        if self.room_group_name:
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        """Inbound traffic is a keepalive only — everything else is server-pushed."""
        try:
            payload = json.loads(text_data)
        except (TypeError, ValueError):
            return

        if payload.get('action') == 'ping':
            await self.send(text_data=json.dumps({'type': 'pong'}))

    async def notification_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'data': event['message'],
        }))
