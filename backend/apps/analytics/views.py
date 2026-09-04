"""
Analytics views - dashboard statistics and metrics.
"""
from datetime import timedelta 
from django .utils import timezone 
from django .db .models import Count ,Q ,Sum 
from django .db import models 
from rest_framework import viewsets ,permissions ,status 
from rest_framework .decorators import action 
from rest_framework .response import Response 

from apps .analytics .models import SystemMetric ,UserActivity ,SecurityDashboardStat 
from apps .analytics .serializers import (
SystemMetricSerializer ,UserActivitySerializer ,
DashboardStatsSerializer ,SecurityStatsSerializer ,
)
from apps .accounts .models import User 
from apps .channels .models import Channel 
from apps .patients .models import Patient ,MedicalRecord 
from apps .audit .models import AuditLog 
from apps .security .permissions import IsAdmin ,IsAuditor 
from django .core .cache import cache 


class DashboardAnalyticsView (viewsets .ViewSet ):
    """
    Dashboard analytics endpoints.
    Provides aggregated statistics for admin dashboards.
    """
    permission_classes =[permissions .IsAuthenticated ]

    @action (detail =False ,methods =['get'])
    def overview (self ,request ):
        """Get dashboard overview statistics with 60-second caching."""
        cache_key ='analytics_dashboard_overview'
        cached_data =cache .get (cache_key )
        if cached_data :
            return Response (cached_data )

        now =timezone .now ()
        today =now .date ()
        week_ago =now -timedelta (days =7 )
        day_ago =now -timedelta (days =1 )

        # Comment_75
        total_users =User .objects .count ()
        active_users =User .objects .filter (is_active =True ).count ()
        users_by_role =User .objects .values ('role').annotate (count =Count ('id'))

        # Comment_76
        total_channels =Channel .objects .count ()
        active_channels =Channel .objects .filter (status =Channel .Status .ACTIVE ).count ()
        channels_by_type =Channel .objects .values ('channel_type').annotate (count =Count ('id'))
        channels_by_priority =Channel .objects .values ('priority').annotate (count =Count ('id'))

        # Comment_77
        total_patients =Patient .objects .count ()
        new_patients_today =Patient .objects .filter (created_at__date =today ).count ()
        new_patients_this_week =Patient .objects .filter (created_at__gte =week_ago ).count ()

        # Comment_78
        total_medical_records =MedicalRecord .objects .count ()
        critical_records =MedicalRecord .objects .filter (is_critical =True ).count ()

        # Comment_79
        security_alerts_today =AuditLog .objects .filter (
        timestamp__date =today ,severity__in =['WARNING','CRITICAL']
        ).count ()
        waf_blocks_today =AuditLog .objects .filter (
        timestamp__date =today ,event_type ='WAF_BLOCKED'
        ).count ()
        failed_logins_today =AuditLog .objects .filter (
        timestamp__date =today ,event_type ='LOGIN_FAILED'
        ).count ()
        biometric_logins_today =AuditLog .objects .filter (
        timestamp__date =today ,event_type ='BIOMETRIC_LOGIN_SUCCESS'
        ).count ()

        # Comment_80
        activity_trend =[]
        for i in range (7 ,-1 ,-1 ):
            day =today -timedelta (days =i )
            count =AuditLog .objects .filter (timestamp__date =day ).count ()
            activity_trend .append ({
            'date':day .isoformat (),
            'count':count ,
            })

        channels_trend =[]
        for i in range (7 ,-1 ,-1 ):
            day =today -timedelta (days =i )
            count =Channel .objects .filter (created_at__date =day ).count ()
            channels_trend .append ({
            'date':day .isoformat (),
            'count':count ,
            })

        patients_trend =[]
        for i in range (7 ,-1 ,-1 ):
            day =today -timedelta (days =i )
            count =Patient .objects .filter (created_at__date =day ).count ()
            patients_trend .append ({
            'date':day .isoformat (),
            'count':count ,
            })

        data ={
        'total_users':total_users ,
        'active_users':active_users ,
        'users_by_role':{item ['role']:item ['count']for item in users_by_role },
        'total_channels':total_channels ,
        'active_channels':active_channels ,
        'channels_by_type':{item ['channel_type']:item ['count']for item in channels_by_type },
        'channels_by_priority':{item ['priority']:item ['count']for item in channels_by_priority },
        'total_patients':total_patients ,
        'new_patients_today':new_patients_today ,
        'new_patients_this_week':new_patients_this_week ,
        'total_medical_records':total_medical_records ,
        'critical_records':critical_records ,
        'security_alerts_today':security_alerts_today ,
        'waf_blocks_today':waf_blocks_today ,
        'failed_logins_today':failed_logins_today ,
        'biometric_logins_today':biometric_logins_today ,
        'activity_trend':activity_trend ,
        'channels_trend':channels_trend ,
        'patients_trend':patients_trend ,
        }

        serializer =DashboardStatsSerializer (data =data )
        serializer .is_valid (raise_exception =True )
        cache .set (cache_key ,serializer .validated_data ,60 )
        return Response (serializer .validated_data )

    @action (detail =False ,methods =['get'])
    def security (self ,request ):
        """Get security-specific analytics with 60-second caching."""
        if request .user .role not in ['SUPER_ADMIN','HOSPITAL_ADMIN','AUDITOR']:
            return Response (
            {'detail':'غير مصرح'},
            status =status .HTTP_403_FORBIDDEN 
            )

        cache_key ='analytics_dashboard_security'
        cached_data =cache .get (cache_key )
        if cached_data :
            return Response (cached_data )

        now =timezone .now ()
        today =now .date ()
        week_ago =now -timedelta (days =7 )

        # Comment_81
        security_events_by_type =AuditLog .objects .filter (
        timestamp__gte =week_ago 
        ).values ('event_type').annotate (count =Count ('id'))

        # Comment_82
        security_events_trend =[]
        for i in range (7 ,-1 ,-1 ):
            day =today -timedelta (days =i )
            count =AuditLog .objects .filter (
            timestamp__date =day ,
            severity__in =['WARNING','CRITICAL']
            ).count ()
            security_events_trend .append ({
            'date':day .isoformat (),
            'count':count ,
            })

            # Comment_83
        from django .db .models import Count 
        from django .core .cache import cache 
        top_blocked =[]
        # Comment_84
        for key in cache ._cache .keys ()if hasattr (cache ._cache ,'keys')else []:
            if key .startswith ('waf_blocked:'):
                ip =key .split (':')[1 ]
                count =cache .get (key ,0 )
                top_blocked .append ({'ip':ip ,'blocks':count })

        top_blocked .sort (key =lambda x :x ['blocks'],reverse =True )
        top_blocked =top_blocked [:10 ]

        # Comment_85
        from apps .security .port_scanner import scan_host_ports 
        try :
            port_result =scan_host_ports ('localhost')
            port_scan_results ={
            'open_ports':port_result ['open_ports'],
            'ports_scanned':port_result ['ports_scanned'],
            'risk_assessment':port_result ['risk_assessment'],
            }
        except Exception :
            port_scan_results ={'open_ports':0 ,'ports_scanned':0 ,'risk_assessment':''}

            # Comment_86
        from apps .security .vulnerability_scanner import run_vulnerability_scan 
        try :
            vuln_report =run_vulnerability_scan ()
            risk_score =vuln_report ['risk_score']
            vulnerabilities_summary =vuln_report ['summary']
        except Exception :
            risk_score =0 
            vulnerabilities_summary ={}

        data ={
        'risk_score':risk_score ,
        'vulnerabilities_summary':vulnerabilities_summary ,
        'security_events_by_type':{
        item ['event_type']:item ['count']for item in security_events_by_type 
        },
        'security_events_trend':security_events_trend ,
        'top_blocked_ips':top_blocked ,
        'port_scan_results':port_scan_results ,
        }

        serializer =SecurityStatsSerializer (data =data )
        serializer .is_valid (raise_exception =True )
        cache .set (cache_key ,serializer .validated_data ,60 )
        return Response (serializer .validated_data )

    @action (detail =False ,methods =['get'])
    def activity_feed (self ,request ):
        """Get recent activity feed."""
        limit =int (request .query_params .get ('limit',20 ))
        limit =min (limit ,100 )

        # Comment_87
        activities =AuditLog .objects .select_related ('user').order_by ('-timestamp')[:limit ]
        feed =[]
        for log in activities :
            feed .append ({
            'id':str (log .id ),
            'user_name':log .user .full_name if log .user else 'النظام',
            'user_email':log .user .email if log .user else '',
            'event_type':log .event_type ,
            'event_type_display':log .get_event_type_display (),
            'severity':log .severity ,
            'ip_address':log .ip_address ,
            'path':log .path ,
            'timestamp':log .timestamp .isoformat (),
            'details':log .details ,
            })

        return Response ({
        'activities':feed ,
        'total':len (feed ),
        })


class UserActivityViewSet (viewsets .ReadOnlyModelViewSet ):
    """View user activities (admin only)."""
    queryset =UserActivity .objects .all ().order_by ('-timestamp')
    serializer_class =UserActivitySerializer 
    permission_classes =[IsAdmin |IsAuditor ]
    filterset_fields =['user','activity_type']
    search_fields =['description','user__email','user__full_name']
    ordering_fields =['timestamp','activity_type']
    ordering =['-timestamp']


class SystemMetricViewSet (viewsets .ReadOnlyModelViewSet ):
    """View system metrics (admin only)."""
    queryset =SystemMetric .objects .all ().order_by ('-date','-hour')
    serializer_class =SystemMetricSerializer 
    permission_classes =[IsAdmin |IsAuditor ]
    filterset_fields =['metric_type','date']
    ordering_fields =['date','hour','value']
    ordering =['-date','-hour']
