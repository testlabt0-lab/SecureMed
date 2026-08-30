"""
URLs for security tools.
"""
from django.urls import path
from apps.security.views import (
    PortScannerView, VulnerabilityScannerView, SecurityDashboardView,
)
from apps.security.stats_views import DashboardStatsView, ActivityFeedView

urlpatterns = [
    path('port-scanner/', PortScannerView.as_view(), name='port-scanner'),
    path('vulnerability-scanner/', VulnerabilityScannerView.as_view(), name='vulnerability-scanner'),
    path('dashboard/', SecurityDashboardView.as_view(), name='security-dashboard'),
    path('stats/', DashboardStatsView.as_view(), name='dashboard-stats'),
    path('activity/', ActivityFeedView.as_view(), name='activity-feed'),
]
