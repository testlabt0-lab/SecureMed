"""
WebSocket Tests for SecureMed
Tests for real-time notification functionality using Django Channels
"""
import pytest
import json
from channels.testing import WebsocketCommunicator
from django.test import TransactionTestCase
from django.contrib.auth import get_user_model
from config.asgi import application
from apps.notifications.models import Notification

User = get_user_model()


class WebSocketNotificationTests(TransactionTestCase):
    """Test WebSocket notifications functionality"""

    @pytest.fixture(autouse=True)
    def setup_test_data(self):
        """Set up test user and notifications"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.superuser = User.objects.create_superuser(
            username='admin',
            password='admin123',
            email='admin@example.com'
        )

    async def test_websocket_connection_authenticated(self):
        """Test that authenticated users can connect to WebSocket"""
        # Create communicator with authenticated scope
        communicator = WebsocketCommunicator(application, "/ws/notifications/")
        
        # Set up authenticated scope
        communicator.scope['user'] = self.user
        
        connected, _ = await communicator.connect()
        
        assert connected is True
        
        # Should receive initial unread count
        response = await communicator.receive_json_from()
        assert response['type'] == 'initial_unread_count'
        assert 'unread_count' in response
        
        await communicator.disconnect()

    async def test_websocket_connection_rejects_anonymous(self):
        """Test that anonymous users are rejected"""
        communicator = WebsocketCommunicator(application, "/ws/notifications/")
        
        # Anonymous user (None)
        communicator.scope['user'] = None
        
        connected, _ = await communicator.connect()
        
        assert connected is False
        
        await communicator.disconnect()

    async def test_receive_new_notification(self):
        """Test receiving a new notification via WebSocket"""
        communicator = WebsocketCommunicator(application, "/ws/notifications/")
        communicator.scope['user'] = self.user
        
        connected, _ = await communicator.connect()
        assert connected
        
        # Receive initial unread count
        initial_response = await communicator.receive_json_from()
        assert initial_response['type'] == 'initial_unread_count'
        initial_count = initial_response['unread_count']
        
        # Create a new notification
        Notification.objects.create(
            recipient=self.user,
            type='info',
            message='Test notification',
            is_read=False
        )
        
        # Send notification through channel layer
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        
        await channel_layer.group_send(
            f'user_{self.user.id}_notifications',
            {
                'type': 'notification_message',
                'notification': {
                    'id': 1,
                    'type': 'info',
                    'message': 'Test notification',
                    'is_read': False,
                    'created_at': '2024-01-01T00:00:00Z'
                }
            }
        )
        
        # Should receive the new notification
        response = await communicator.receive_json_from()
        assert response['type'] == 'new_notification'
        assert response['notification']['message'] == 'Test notification'
        
        await communicator.disconnect()

    async def test_mark_notifications_read(self):
        """Test marking notifications as read via WebSocket"""
        communicator = WebsocketCommunicator(application, "/ws/notifications/")
        communicator.scope['user'] = self.user
        
        connected, _ = await communicator.connect()
        assert connected
        
        # Receive initial unread count
        await communicator.receive_json_from()
        
        # Create test notifications
        notification = Notification.objects.create(
            recipient=self.user,
            type='info',
            message='Test notification',
            is_read=False
        )
        
        # Send mark_read message
        await communicator.send_json_to({
            'type': 'mark_read',
            'notification_ids': [notification.id]
        })
        
        # Should receive updated unread count
        response = await communicator.receive_json_from()
        assert response['type'] == 'unread_count_updated'
        
        # Verify notification is marked as read in database
        notification.refresh_from_db()
        assert notification.is_read is True
        
        await communicator.disconnect()

    async def test_unread_count_updates(self):
        """Test that unread count updates correctly"""
        communicator = WebsocketCommunicator(application, "/ws/notifications/")
        communicator.scope['user'] = self.user
        
        connected, _ = await communicator.connect()
        assert connected
        
        # Receive initial unread count (should be 0)
        initial_response = await communicator.receive_json_from()
        assert initial_response['unread_count'] == 0
        
        # Create multiple notifications
        for i in range(3):
            Notification.objects.create(
                recipient=self.user,
                type='info',
                message=f'Test notification {i}',
                is_read=False
            )
        
        # Trigger unread count update by sending mark_read for one
        await communicator.send_json_to({
            'type': 'mark_read',
            'notification_ids': []
        })
        
        # Should receive updated count
        response = await communicator.receive_json_from()
        assert response['type'] == 'unread_count_updated'
        assert response['unread_count'] == 3
        
        await communicator.disconnect()


class UpdateConsumerTests(TransactionTestCase):
    """Tests for the general UpdateConsumer"""

    @pytest.fixture(autouse=True)
    def setup_test_data(self):
        """Set up test user"""
        self.user = User.objects.create_user(
            username='testuser2',
            password='testpass123',
            email='test2@example.com'
        )

    async def test_update_consumer_room_connection(self):
        """Test connecting to update room"""
        communicator = WebsocketCommunicator(
            application, 
            "/ws/updates/test_room/"
        )
        communicator.scope['user'] = self.user
        
        connected, _ = await communicator.connect()
        
        assert connected is True
        
        await communicator.disconnect()

    async def test_update_consumer_rejects_anonymous(self):
        """Test that anonymous users are rejected from update rooms"""
        communicator = WebsocketCommunicator(
            application,
            "/ws/updates/test_room/"
        )
        communicator.scope['user'] = None
        
        connected, _ = await communicator.connect()
        
        assert connected is False
        
        await communicator.disconnect()
