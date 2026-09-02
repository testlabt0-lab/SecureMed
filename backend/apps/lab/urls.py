"""Lab URL routes."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import LabTestViewSet, LabOrderViewSet, LabResultViewSet, LabStatsView

router = DefaultRouter()
router.register(r'tests', LabTestViewSet, basename='lab-test')
router.register(r'orders', LabOrderViewSet, basename='lab-order')
router.register(r'results', LabResultViewSet, basename='lab-result')
router.register(r'stats', LabStatsView, basename='lab-stats')

urlpatterns = [
    path('', include(router.urls)),
]
