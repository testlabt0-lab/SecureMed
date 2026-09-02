"""
URLs for reports app.
"""
from django.urls import path

from apps.reports.views import (
    ChannelReportPDFView, AuditExcelView, MonthlyReportPDFView,
    MonthlyReportEmailView, ReportListView, UnifiedReportDownloadView,
)

urlpatterns = [
    path('list/', ReportListView.as_view(), name='report-list'),
    path('channel/<uuid:channel_id>/pdf/', ChannelReportPDFView.as_view(), name='report-channel-pdf'),
    path('audit/excel/', AuditExcelView.as_view(), name='report-audit-excel'),
    path('monthly/pdf/', MonthlyReportPDFView.as_view(), name='report-monthly-pdf'),
    path('monthly/email/', MonthlyReportEmailView.as_view(), name='report-monthly-email'),
    path('<str:report_id>/', UnifiedReportDownloadView.as_view(), name='report-download'),
]

