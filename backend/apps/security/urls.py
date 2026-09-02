"""
URLs for security tools.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.security.views import (
    PortScannerView, VulnerabilityScannerView, SecurityDashboardView,
)
from apps.security.stats_views import DashboardStatsView, ActivityFeedView
from apps.security.blocklist_views import (
    DeviceRegistryViewSet, BlockedDeviceViewSet, BlockedIPViewSet, LoginHistoryViewSet
)

router = DefaultRouter()
router.register(r'devices', DeviceRegistryViewSet, basename='devices')
router.register(r'blocked-devices', BlockedDeviceViewSet, basename='blocked-devices')
router.register(r'blocked-ips', BlockedIPViewSet, basename='blocked-ips')
router.register(r'login-history', LoginHistoryViewSet, basename='login-history')

urlpatterns = [
    path('port-scanner/', PortScannerView.as_view(), name='port-scanner'),
    path('vulnerability-scanner/', VulnerabilityScannerView.as_view(), name='vulnerability-scanner'),
    path('dashboard/', SecurityDashboardView.as_view(), name='security-dashboard'),
    path('stats/', DashboardStatsView.as_view(), name='dashboard-stats'),
    path('activity/', ActivityFeedView.as_view(), name='activity-feed'),
    path('device-types/', DeviceRegistryViewSet.as_view({'get': 'types'}), name='device-types'),
    path('', include(router.urls)),
]
