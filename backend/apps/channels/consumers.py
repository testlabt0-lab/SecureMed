"""Live in-channel chat over WebSocket.

The REST `channels.messages` action stays the source of truth — this consumer
broadcasts what it persists, so a client that polls REST and a client on the
socket see the same thread. Group name is derived from the channel UUID; the
join check is the same ``Channel.can_view`` rule the REST layer enforces, so
membership revocation takes effect on the next (re)connect and mid-session
listeners are the accepted residual risk of any socket session.
"""
import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger('security')

CLOSE_UNAUTHENTICATED = 4001
CLOSE_FORBIDDEN = 4003
CLOSE_CHANNEL_UNKNOWN = 4004

MAX_BODY_LEN = 4000


class ChannelChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.channel_id = self.scope['url_route']['kwargs']['channel_id']
        self.group_name = f'channel_chat_{self.channel_id}'
        self.user = self.scope['user']

        if not self.user or not self.user.is_authenticated:
            await self.close(code=CLOSE_UNAUTHENTICATED)
            return

        permitted = await self._authorise()
        if not permitted:
            logger.info(
                'ws channel_chat denied: user %s on channel %s',
                self.user.id, self.channel_id,
            )
            await self.close(code=CLOSE_FORBIDDEN)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept(subprotocol=self.scope.get('ws_subprotocol'))

    @database_sync_to_async
    def _authorise(self):
        """Same visibility rule the REST layer enforces (Channel.can_view)."""
        from apps.channels.models import Channel
        channel = Channel.objects.filter(pk=self.channel_id).first()
        if channel is None:
            return False
        return channel.can_view(self.user)

    async def disconnect(self, close_code):
        if getattr(self, 'group_name', None):
            await self.channel_layer.group_discard(
                self.group_name, self.channel_name
            )

    async def receive(self, text_data):
        if not getattr(self, 'group_name', None):
            return
        try:
            payload = json.loads(text_data)
        except (TypeError, ValueError):
            await self.send(text_data=json.dumps({
                'type': 'error', 'detail': 'رسالة غير صالحة',
            }))
            return
        if not isinstance(payload, dict):
            return

        body = str(payload.get('body') or '').strip()
        if not body:
            return
        if len(body) > MAX_BODY_LEN:
            await self.send(text_data=json.dumps({
                'type': 'error', 'detail': 'الرسالة طويلة جداً',
            }))
            return

        message = await self._persist_message(body)
        if message is None:
            await self.send(text_data=json.dumps({
                'type': 'error', 'detail': 'فقدت عضويتك في هذه القناة',
            }))
            return

        await self.channel_layer.group_send(self.group_name, {
            'type': 'chat_message',
            'message': message,
        })

    @database_sync_to_async
    def _persist_message(self, body):
        """Save the message through the same model rules as the REST path.

        Returns the serialised message, or None when the sender's membership
        lapsed between connect and send — the same check the REST action makes.
        """
        from apps.channels.models import Channel, ChannelMessage
        from apps.channels.serializers import ChannelMessageSerializer

        try:
            channel = Channel.objects.get(pk=self.channel_id)
        except Channel.DoesNotExist:
            return None

        is_admin = self.user.role in ('SUPER_ADMIN', 'HOSPITAL_ADMIN')
        membership = channel.memberships.filter(
            user=self.user, is_active=True
        ).exists()
        if not (is_admin or channel.owner_id == self.user.id or membership):
            return None

        message = ChannelMessage.objects.create(
            channel=channel, sender=self.user, body=body
        )
        from apps.audit.utils import log_security_event
        log_security_event(
            user=self.user,
            event_type='CHANNEL_MESSAGE_SENT',
            details={
                'channel_id': str(channel.id),
                'message_id': str(message.id),
                'via': 'websocket',
            },
        )
        return ChannelMessageSerializer(message).data

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message'],
        }))
