"""URLs for the backups app."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.backups.views import BackupViewSet

router = DefaultRouter()
router.register(r'', BackupViewSet, basename='backup')

urlpatterns = [
    path('', include(router.urls)),
]
