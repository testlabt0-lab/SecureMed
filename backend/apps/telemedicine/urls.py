"""Telemedicine URL routes."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ConsultationViewSet, ChatMessageViewSet

router = DefaultRouter()
router.register(r'consultations', ConsultationViewSet, basename='consultation')
router.register(r'messages', ChatMessageViewSet, basename='chat-message')

urlpatterns = [
    path('', include(router.urls)),
]
