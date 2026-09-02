"""Billing URL routes."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    InsuranceProviderViewSet,
    PatientInsuranceViewSet,
    InvoiceViewSet,
    BillingStatsView,
)

router = DefaultRouter()
router.register(r'insurance-providers', InsuranceProviderViewSet, basename='insurance-provider')
router.register(r'patient-insurance', PatientInsuranceViewSet, basename='patient-insurance')
router.register(r'invoices', InvoiceViewSet, basename='invoice')
router.register(r'stats', BillingStatsView, basename='billing-stats')

urlpatterns = [
    path('', include(router.urls)),
]
