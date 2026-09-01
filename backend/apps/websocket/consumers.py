"""
WebSocket consumers for SecureMed
Provides real-time notifications and updates
"""
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time notifications
    Replaces the polling mechanism in useRealtimeNotifications hook
    """
    
    async def connect(self):
        self.user = self.scope["user"]
        
        # Reject anonymous connections
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return
        
        # Join user-specific notification group
        self.notification_group_name = f"user_{self.user.id}_notifications"
        
        await self.channel_layer.group_add(
            self.notification_group_name,
            self.channel_name
        )
        
        await self.accept()
        logger.info(f"WebSocket connected for user {self.user.id}")
        
        # Send initial unread count
        unread_count = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            'type': 'initial_unread_count',
            'unread_count': unread_count
        }))

    async def disconnect(self, close_code):
        # Leave notification group
        if hasattr(self, 'notification_group_name'):
            await self.channel_layer.group_discard(
                self.notification_group_name,
                self.channel_name
            )
        logger.info(f"WebSocket disconnected for user {self.user.id if hasattr(self, 'user') else 'unknown'}")

    async def receive(self, text_data):
        """Handle incoming messages from WebSocket"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'mark_read':
                # Mark notifications as read
                notification_ids = data.get('notification_ids', [])
                await self.mark_notifications_read(notification_ids)
                
                # Update unread count
                unread_count = await self.get_unread_count()
                await self.send(text_data=json.dumps({
                    'type': 'unread_count_updated',
                    'unread_count': unread_count
                }))
                
        except json.JSONDecodeError:
            logger.error("Invalid JSON received in WebSocket")
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {e}")

    async def notification_message(self, event):
        """
        Handler for receiving notifications from the group
        Sends notification to the WebSocket client
        """
        await self.send(text_data=json.dumps({
            'type': 'new_notification',
            'notification': event['notification']
        }))

    async def update_unread_count(self, event):
        """Handler for updating unread count"""
        await self.send(text_data=json.dumps({
            'type': 'unread_count_updated',
            'unread_count': event['unread_count']
        }))

    @database_sync_to_async
    def get_unread_count(self):
        """Get unread notification count for user"""
        from apps.notifications.models import Notification
        return Notification.objects.filter(
            recipient=self.user,
            is_read=False
        ).count()

    @database_sync_to_async
    def mark_notifications_read(self, notification_ids):
        """Mark notifications as read"""
        from apps.notifications.models import Notification
        Notification.objects.filter(
            id__in=notification_ids,
            recipient=self.user
        ).update(is_read=True)


class UpdateConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for general system updates
    Can be used for real-time dashboard updates, patient status changes, etc.
    """
    
    async def connect(self):
        self.user = self.scope["user"]
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return
        
        # Join room group
        self.room_group_name = f"room_{self.room_name}"
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        logger.info(f"WebSocket connected to room {self.room_name} by user {self.user.id}")

    async def disconnect(self, close_code):
        # Leave room group
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        """Handle incoming messages"""
        data = json.loads(text_data)
        # Process update messages as needed
        logger.info(f"Received update in room {self.room_name}: {data}")

    async def update_message(self, event):
        """Send update to WebSocket client"""
        await self.send(text_data=json.dumps(event['data']))
