import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger('webrtc')

class VideoCallConsumer(AsyncWebsocketConsumer):
    """
    Signaling Server for WebRTC Telemedicine calls.
    Exchanges SDP offers/answers and ICE candidates between peers (Doctor <-> Patient).
    """
    async def connect(self):
        self.user = self.scope["user"]
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'video_call_{self.room_name}'

        # In a real app, verify if the user has access to this room (appointment ID)
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
        logger.info(f"User joined WebRTC room: {self.room_group_name}")

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket (from a peer)
    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')
        payload = data.get('payload')
        
        # We only route specific WebRTC signaling messages
        if message_type in ['offer', 'answer', 'ice_candidate', 'user_joined', 'user_left']:
            # Broadcast the signaling message to everyone ELSE in the room
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'webrtc_signal',
                    'message_type': message_type,
                    'payload': payload,
                    'sender_channel_name': self.channel_name
                }
            )

    # Receive message from room group (broadcast to peers)
    async def webrtc_signal(self, event):
        message_type = event['message_type']
        payload = event['payload']
        sender_channel_name = event['sender_channel_name']
        
        # Send message to WebSocket, but NOT back to the sender
        if self.channel_name != sender_channel_name:
            await self.send(text_data=json.dumps({
                'type': message_type,
                'payload': payload
            }))
