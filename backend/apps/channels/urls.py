"""
URLs for channels app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.channels.views import ChannelViewSet, ChannelInvitationViewSet

router = DefaultRouter()
router.register(r'', ChannelViewSet, basename='channel')
router.register(r'invitations', ChannelInvitationViewSet, basename='invitation')

urlpatterns = [
    path('', include(router.urls)),
]
