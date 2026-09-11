"""
URLs for security tools.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.security.views import (
    PortScannerView, VulnerabilityScannerView, SecurityDashboardView,
    CheckDeviceView, TelegramWebhookView, ActiveSessionsView, MyDevicesView,
    ZTNARequestView, ZTNAStatusView,
)
from apps.security.stats_views import DashboardStatsView, ActivityFeedView
from apps.security.blocklist_views import (
    DeviceRegistryViewSet, BlockedDeviceViewSet, BlockedIPViewSet, LoginHistoryViewSet
)
from apps.security.license_views import DeviceLicenseViewSet

router = DefaultRouter()
router.register(r'devices', DeviceRegistryViewSet, basename='devices')
router.register(r'licenses', DeviceLicenseViewSet, basename='licenses')
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
    path('check-device/', CheckDeviceView.as_view(), name='check-device'),
    path('my-devices/', MyDevicesView.as_view(), name='my-devices'),
    path('sessions/', ActiveSessionsView.as_view(), name='active-sessions'),
    path('telegram-webhook/', TelegramWebhookView.as_view(), name='telegram-webhook'),
    path('ztna-request/', ZTNARequestView.as_view(), name='ztna-request'),
    path('ztna-status/', ZTNAStatusView.as_view(), name='ztna-status'),
    path('', include(router.urls)),
]
