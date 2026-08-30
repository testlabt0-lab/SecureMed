"""URLs for the basins app."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.basins.views import BasinViewSet

router = DefaultRouter()
router.register(r'', BasinViewSet, basename='basin')

urlpatterns = [
    path('', include(router.urls)),
]
