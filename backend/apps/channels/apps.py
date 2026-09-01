"""Channels app configuration."""

from django.apps import AppConfig


class ChannelsAppConfig(AppConfig):
    """Configuration for the channels app."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.channels'
    verbose_name = 'Channels & WebSocket Rooms'
    
    def ready(self):
        """Initialize channels app when Django starts."""
        # Import signals if needed
        pass
