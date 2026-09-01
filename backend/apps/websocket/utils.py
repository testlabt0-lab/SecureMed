"""
Utility functions for sending WebSocket notifications
"""
import logging
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)


def send_notification_to_user(user_id, notification_data):
    """
    Send a real-time notification to a specific user via WebSocket
    
    Args:
        user_id: The ID of the user to notify
        notification_data: Dict containing notification details
    """
    channel_layer = get_channel_layer()
    
    if not channel_layer:
        logger.warning("Channel layer not configured, falling back to polling")
        return
    
    try:
        # Send to user's notification group
        async_to_sync(channel_layer.group_send)(
            f"user_{user_id}_notifications",
            {
                'type': 'notification_message',
                'notification': notification_data
            }
        )
        
        # Also send unread count update
        from apps.notifications.models import Notification
        unread_count = Notification.objects.filter(
            recipient_id=user_id,
            is_read=False
        ).count()
        
        async_to_sync(channel_layer.group_send)(
            f"user_{user_id}_notifications",
            {
                'type': 'update_unread_count',
                'unread_count': unread_count
            }
        )
        
        logger.debug(f"Sent WebSocket notification to user {user_id}")
    except Exception as e:
        logger.error(f"Failed to send WebSocket notification to user {user_id}: {e}")


def send_update_to_room(room_name, data):
    """
    Send an update to all clients in a room
    
    Args:
        room_name: The name of the room/group
        data: Dict containing update data
    """
    channel_layer = get_channel_layer()
    
    if not channel_layer:
        logger.warning("Channel layer not configured")
        return
    
    try:
        async_to_sync(channel_layer.group_send)(
            f"room_{room_name}",
            {
                'type': 'update_message',
                'data': data
            }
        )
        logger.debug(f"Sent update to room {room_name}")
    except Exception as e:
        logger.error(f"Failed to send update to room {room_name}: {e}")
