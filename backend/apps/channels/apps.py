from django.apps import AppConfig

class ChannelsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.channels'
    label = 'app_channels'  # To avoid conflict with the django-channels library
