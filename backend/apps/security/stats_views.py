"""
Statistics and analytics endpoints for dashboard.
"""
from rest_framework import status ,permissions 
from rest_framework .views import APIView 
from rest_framework .response import Response 
from django .db .models import Count ,Q ,Avg 
from django .utils import timezone 
from datetime import timedelta 

from apps .accounts .models import User 
from apps .channels .models import Channel ,ChannelMembership 
from apps .patients .models import Patient ,MedicalRecord 
from apps .audit .models import AuditLog 


class DashboardStatsView (APIView ):
    """Get dashboard statistics for the current user with intelligent caching."""
    permission_classes =[permissions .IsAuthenticated ]

    def get (self ,request ):
        user =request .user 
        cache_key = f"dashboard_stats_{user.id}_{user.role}"
        from django.core.cache import cache
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)

        from django .db .models import Q, Count

        # Base query for accessible channels
        if user .role in ['SUPER_ADMIN','HOSPITAL_ADMIN']:
            channels =Channel .objects .all ()
            patients =Patient .objects .all ()
        else :
            channels =Channel .objects .filter (
            Q (owner =user )|Q (memberships__user =user ,memberships__is_active =True )
            ).distinct ()
            patients =Patient .objects .filter (channels__in =channels ).distinct ()

        # Channel stats in 1 aggregated query
        ch_aggr = channels.aggregate(
            total=Count('id'),
            active=Count('id', filter=Q(status=Channel.Status.ACTIVE)),
            urgent=Count('id', filter=Q(priority='URGENT'))
        )
        total_channels = ch_aggr['total'] or 0
        active_channels = ch_aggr['active'] or 0
        urgent_channels = ch_aggr['urgent'] or 0

        # Patient stats
        total_patients = patients.count()

        # Record stats in 1 aggregated query
        accessible_channel_ids = list(channels.values_list('id', flat=True))
        records = MedicalRecord.objects.filter(channel_id__in=accessible_channel_ids)
        rec_aggr = records.aggregate(
            total=Count('id'),
            critical=Count('id', filter=Q(is_critical=True))
        )
        total_records = rec_aggr['total'] or 0
        critical_records = rec_aggr['critical'] or 0

        # User stats (admin only)
        user_stats = {}
        if user.role in ['SUPER_ADMIN', 'HOSPITAL_ADMIN']:
            u_aggr = User.objects.aggregate(
                total=Count('id'),
                active=Count('id', filter=Q(is_active=True)),
                biometric=Count('id', filter=Q(is_biometric_enabled=True))
            )
            role_counts = dict(User.objects.values('role').annotate(count=Count('id')).values_list('role', 'count'))
            user_stats = {
                'total_users': u_aggr['total'] or 0,
                'active_users': u_aggr['active'] or 0,
                'biometric_enabled': u_aggr['biometric'] or 0,
                'by_role': {
                    role: role_counts.get(role, 0)
                    for role, _ in User.Role.choices
                },
            }

        # Recent activity (last 7 days) in 1 aggregated query
        seven_days_ago = timezone.now() - timedelta(days=7)
        recent_audit = AuditLog.objects.filter(timestamp__gte=seven_days_ago)
        aud_aggr = recent_audit.aggregate(
            total=Count('id'),
            critical=Count('id', filter=Q(severity=AuditLog.Severity.CRITICAL)),
            warnings=Count('id', filter=Q(severity=AuditLog.Severity.WARNING))
        )
        audit_stats = {
            'total_events': aud_aggr['total'] or 0,
            'critical_events': aud_aggr['critical'] or 0,
            'warnings': aud_aggr['warnings'] or 0,
        }

        # Channels by type (1 query)
        channels_by_type = channels.values('channel_type').annotate(count=Count('id'))
        channels_by_type_dict = {item['channel_type']: item['count'] for item in channels_by_type}

        # Channels by priority (1 grouped query instead of 4 separate queries)
        priority_counts = dict(channels.values('priority').annotate(count=Count('id')).values_list('priority', 'count'))
        channels_by_priority = {
            p: priority_counts.get(p, 0) for p in ['LOW', 'MEDIUM', 'HIGH', 'URGENT']
        }

        # Records by type (1 query)
        records_by_type = records.values('record_type').annotate(count=Count('id'))
        records_by_type_dict = {item['record_type']: item['count'] for item in records_by_type}

        # Device stats (1 query)
        from apps.security.models import DeviceRegistry 
        device_queryset = list(DeviceRegistry.objects.filter(user=user))
        from apps.security.middleware import WAFMiddleware
        middleware = WAFMiddleware(lambda r: None)
        device_type_counts = {}
        trusted_count = 0
        for device in device_queryset:
            dtype = middleware._detect_device_type(device.device_fingerprint)
            device_type_counts[dtype] = device_type_counts.get(dtype, 0) + 1
            if device.is_trusted:
                trusted_count += 1

        device_stats = {
            'total_devices': len(device_queryset),
            'by_type': device_type_counts,
            'trusted': trusted_count,
        }

        response_data = {
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
            'devices': device_stats,
        }

        cache.set(cache_key, response_data, timeout=60)
        return Response(response_data)

    def _get_trends (self ,channel_ids ):
        """Get 7-day trend data using 2 batched queries instead of 14."""
        today = timezone.now().date()
        start_date = today - timedelta(days=6)
        start_dt = timezone.make_aware(timezone.datetime.combine(start_date, timezone.datetime.min.time()))

        # Group channel creations by date
        channel_dates = list(Channel.objects.filter(
            id__in=channel_ids,
            created_at__gte=start_dt
        ).values_list('created_at', flat=True))

        record_dates = list(MedicalRecord.objects.filter(
            channel_id__in=channel_ids,
            created_at__gte=start_dt
        ).values_list('created_at', flat=True))

        from collections import Counter
        ch_counter = Counter(dt.date().isoformat() for dt in channel_dates if dt)
        rec_counter = Counter(dt.date().isoformat() for dt in record_dates if dt)

        trends = []
        for i in range(7):
            day_str = (today - timedelta(days=6 - i)).isoformat()
            trends.append({
                'date': day_str,
                'channels': ch_counter.get(day_str, 0),
                'records': rec_counter.get(day_str, 0),
            })
        return trends 


class ActivityFeedView (APIView ):
    """Get recent activity feed for the current user."""
    permission_classes =[permissions .IsAuthenticated ]

    def get (self ,request ):
        user =request .user 
        from django .db .models import Q 

        # Get accessible channels
        if user .role in ['SUPER_ADMIN','HOSPITAL_ADMIN']:
            channels =Channel .objects .all ()
        else :
            channels =Channel .objects .filter (
            Q (owner =user )|Q (memberships__user =user ,memberships__is_active =True )
            ).distinct ()

        accessible_channel_ids =channels .values_list ('id',flat =True )

        # Get recent records
        recent_records =MedicalRecord .objects .filter (
        channel_id__in =accessible_channel_ids 
        ).select_related ('channel','created_by').order_by ('-created_at')[:10 ]

        activities =[]
        for record in recent_records :
            activities .append ({
            'id':str (record .id ),
            'type':'record_created',
            'title':record .title ,
            'description':record .content [:100 ]+'...'if len (record .content )>100 else record .content ,
            'channel_name':record .channel .name ,
            'channel_id':str (record .channel .id ),
            'created_by':record .created_by .full_name ,
            'record_type':record .record_type ,
            'record_type_display':record .get_record_type_display (),
            'is_critical':record .is_critical ,
            'timestamp':record .created_at .isoformat (),
            })

        return Response ({
        'activities':activities ,
        'count':len (activities ),
        })
