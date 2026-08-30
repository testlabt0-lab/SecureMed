"""
Notifications URLs.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.notifications.views import (
    NotificationViewSet, NotificationPreferenceViewSet,
)

router = DefaultRouter()
router.register(r'', NotificationViewSet, basename='notification')
router.register(r'preferences', NotificationPreferenceViewSet, basename='preferences')

urlpatterns = [
    path('', include(router.urls)),
]
