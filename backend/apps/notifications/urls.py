"""
Notifications URLs.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.notifications.views import (
    NotificationViewSet, NotificationPreferenceView,
    PushTokenRegisterView,
)

router = DefaultRouter()
router.register(r'', NotificationViewSet, basename='notification')

urlpatterns = [
    # Must come before the router include. NotificationViewSet is registered at
    # prefix '', so the router generates a detail route ^(?P<pk>[^/.]+)/$ that
    # matches literally any single segment — including 'preferences'. Anything
    # mounted under this app has to be declared ahead of that catch-all.
    path(
        'preferences/',
        NotificationPreferenceView.as_view(),
        name='notification-preferences',
    ),
    path(
        'push/register/',
        PushTokenRegisterView.as_view(),
        name='push-token-register',
    ),
    path('', include(router.urls)),
]
