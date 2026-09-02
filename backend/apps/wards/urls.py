"""Ward management URL routes."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    WardViewSet,
    RoomViewSet,
    BedViewSet,
    BedAssignmentViewSet,
    WardStatsView,
)

router = DefaultRouter()
router.register(r'wards', WardViewSet, basename='ward')
router.register(r'rooms', RoomViewSet, basename='room')
router.register(r'beds', BedViewSet, basename='bed')
router.register(r'assignments', BedAssignmentViewSet, basename='bed-assignment')
router.register(r'stats', WardStatsView, basename='ward-stats')

urlpatterns = [
    path('', include(router.urls)),
]
