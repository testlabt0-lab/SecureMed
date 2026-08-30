"""
Statistics and analytics endpoints for dashboard.
"""
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Count, Q, Avg
from django.utils import timezone
from datetime import timedelta

from apps.accounts.models import User
from apps.channels.models import Channel, ChannelMembership
from apps.patients.models import Patient, MedicalRecord
from apps.audit.models import AuditLog


class DashboardStatsView(APIView):
    """Get dashboard statistics for the current user."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        from django.db.models import Q

        # Base query for accessible channels
        if user.role in ['SUPER_ADMIN', 'HOSPITAL_ADMIN']:
            channels = Channel.objects.all()
            patients = Patient.objects.all()
        else:
            channels = Channel.objects.filter(
                Q(owner=user) | Q(memberships__user=user, memberships__is_active=True)
            ).distinct()
            patients = Patient.objects.filter(channels__in=channels).distinct()

        # Channel stats
        total_channels = channels.count()
        active_channels = channels.filter(status=Channel.Status.ACTIVE).count()
        urgent_channels = channels.filter(priority='URGENT').count()

        # Patient stats
        total_patients = patients.count()

        # Record stats
        accessible_channel_ids = channels.values_list('id', flat=True)
        records = MedicalRecord.objects.filter(channel_id__in=accessible_channel_ids)
        total_records = records.count()
        critical_records = records.filter(is_critical=True).count()

        # User stats (admin only)
        user_stats = {}
        if user.role in ['SUPER_ADMIN', 'HOSPITAL_ADMIN']:
            user_stats = {
                'total_users': User.objects.count(),
                'active_users': User.objects.filter(is_active=True).count(),
                'biometric_enabled': User.objects.filter(is_biometric_enabled=True).count(),
                'by_role': {
                    role: User.objects.filter(role=role).count()
                    for role, _ in User.Role.choices
                },
            }

        # Recent activity (last 7 days)
        seven_days_ago = timezone.now() - timedelta(days=7)
        recent_audit = AuditLog.objects.filter(timestamp__gte=seven_days_ago)
        audit_stats = {
            'total_events': recent_audit.count(),
            'critical_events': recent_audit.filter(severity=AuditLog.Severity.CRITICAL).count(),
            'warnings': recent_audit.filter(severity=AuditLog.Severity.WARNING).count(),
        }

        # Channels by type
        channels_by_type = channels.values('channel_type').annotate(
            count=Count('id')
        ).order_by('channel_type')
        channels_by_type_dict = {
            item['channel_type']: item['count'] for item in channels_by_type
        }

        # Channels by priority
        channels_by_priority = {}
        for priority in ['LOW', 'MEDIUM', 'HIGH', 'URGENT']:
            channels_by_priority[priority] = channels.filter(priority=priority).count()

        # Records by type
        records_by_type = records.values('record_type').annotate(
            count=Count('id')
        ).order_by('record_type')
        records_by_type_dict = {
            item['record_type']: item['count'] for item in records_by_type
        }

        return Response({
            'channels': {
                'total': total_channels,
                'active': active_channels,
                'urgent': urgent_channels,
                'by_type': channels_by_type_dict,
                'by_priority': channels_by_priority,
            },
            'patients': {
                'total': total_patients,
            },
            'records': {
                'total': total_records,
                'critical': critical_records,
                'by_type': records_by_type_dict,
            },
            'users': user_stats,
            'audit': audit_stats,
            'trends': self._get_trends(accessible_channel_ids),
        })

    def _get_trends(self, channel_ids):
        """Get 7-day trend data."""
        today = timezone.now().date()
        trends = []
        for i in range(7):
            day = today - timedelta(days=6 - i)
            day_start = timezone.datetime.combine(day, timezone.datetime.min.time())
            day_end = timezone.datetime.combine(day, timezone.datetime.max.time())
            day_start = timezone.make_aware(day_start)
            day_end = timezone.make_aware(day_end)

            channels_count = Channel.objects.filter(
                id__in=channel_ids,
                created_at__range=(day_start, day_end)
            ).count()

            records_count = MedicalRecord.objects.filter(
                channel_id__in=channel_ids,
                created_at__range=(day_start, day_end)
            ).count()

            trends.append({
                'date': day.isoformat(),
                'channels': channels_count,
                'records': records_count,
            })
        return trends


class ActivityFeedView(APIView):
    """Get recent activity feed for the current user."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        from django.db.models import Q

        # Get accessible channels
        if user.role in ['SUPER_ADMIN', 'HOSPITAL_ADMIN']:
            channels = Channel.objects.all()
        else:
            channels = Channel.objects.filter(
                Q(owner=user) | Q(memberships__user=user, memberships__is_active=True)
            ).distinct()

        accessible_channel_ids = channels.values_list('id', flat=True)

        # Get recent records
        recent_records = MedicalRecord.objects.filter(
            channel_id__in=accessible_channel_ids
        ).select_related('channel', 'created_by').order_by('-created_at')[:10]

        activities = []
        for record in recent_records:
            activities.append({
                'id': str(record.id),
                'type': 'record_created',
                'title': record.title,
                'description': record.content[:100] + '...' if len(record.content) > 100 else record.content,
                'channel_name': record.channel.name,
                'channel_id': str(record.channel.id),
                'created_by': record.created_by.full_name,
                'record_type': record.record_type,
                'record_type_display': record.get_record_type_display(),
                'is_critical': record.is_critical,
                'timestamp': record.created_at.isoformat(),
            })

        return Response({
            'activities': activities,
            'count': len(activities),
        })
