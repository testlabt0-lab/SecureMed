"""Pharmacy URL routes."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    MedicationViewSet,
    DrugInteractionViewSet,
    PrescriptionViewSet,
    PharmacyStatsView,
)

router = DefaultRouter()
router.register(r'medications', MedicationViewSet, basename='medication')
router.register(r'interactions', DrugInteractionViewSet, basename='drug-interaction')
router.register(r'prescriptions', PrescriptionViewSet, basename='prescription')
router.register(r'stats', PharmacyStatsView, basename='pharmacy-stats')

urlpatterns = [
    path('', include(router.urls)),
]
