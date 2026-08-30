"""
URLs for audit app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.audit.views import AuditLogViewSet

router = DefaultRouter()
router.register(r'logs', AuditLogViewSet, basename='audit-log')

urlpatterns = [
    path('', include(router.urls)),
]
