import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import AnonymousUser

logger = logging.getLogger('notifications')

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        
        # Check authentication (Simple JWT is in HTTP header, Channels might need token in query param or custom middleware)
        # For simplicity, if using AuthMiddlewareStack, it checks session auth.
        # In a real JWT app, we need a custom JWTAuthMiddleware. We will add a basic check for now.
        
        # For now, allow the connection and we will build the JWT auth middleware later.
        # Let's bind them to their own user channel
        if self.user.is_authenticated:
            self.room_group_name = f'user_{self.user.id}'
            
            # Join room group
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            await self.accept()
        else:
            # Deny connection if not authenticated
            # Note: We will need a JWT middleware for this to work correctly with React.
            await self.accept()
            # We accept then close to send a friendly error or just close
            # await self.close(code=4001)

    async def disconnect(self, close_code):
        # Leave room group
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    # Receive message from WebSocket
    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            action = text_data_json.get('action')
            
            # We don't expect the client to send much, mostly they receive.
            # But they could send a 'ping' or 'mark_read'
            if action == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong'
                }))
        except Exception as e:
            logger.error(f"Error in NotificationConsumer receive: {str(e)}")

    # Receive message from room group (Channel layer)
    async def notification_message(self, event):
        message = event['message']
        
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'data': message
        }))
