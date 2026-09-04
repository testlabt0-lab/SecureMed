from unfold.admin import ModelAdmin
"""
Admin for analytics app.
"""
from django.contrib import admin
from apps.analytics.models import SystemMetric, UserActivity, SecurityDashboardStat


@admin.register(SystemMetric)
class SystemMetricAdmin(ModelAdmin):
    list_display = ('metric_type', 'value', 'date', 'hour')
    list_filter = ('metric_type', 'date')
    readonly_fields = ('created_at',)


@admin.register(UserActivity)
class UserActivityAdmin(ModelAdmin):
    list_display = ('user', 'activity_type', 'timestamp', 'ip_address')
    list_filter = ('activity_type',)
    search_fields = ('user__email', 'description')
    date_hierarchy = 'timestamp'


@admin.register(SecurityDashboardStat)
class SecurityDashboardStatAdmin(ModelAdmin):
    list_display = ('stat_key', 'last_updated')
    search_fields = ('stat_key',)
    readonly_fields = ('last_updated',)
