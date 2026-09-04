"""
Analytics serializers.
"""
from rest_framework import serializers 
from apps .analytics .models import SystemMetric ,UserActivity ,SecurityDashboardStat 


class SystemMetricSerializer (serializers .ModelSerializer ):
    """Serializer for SystemMetric."""
    metric_type_display =serializers .CharField (source ='get_metric_type_display',read_only =True )

    class Meta :
        model =SystemMetric 
        fields =[
        'id','metric_type','metric_type_display','value',
        'date','hour','metadata','created_at',
        ]
        read_only_fields =fields 


class UserActivitySerializer (serializers .ModelSerializer ):
    """Serializer for UserActivity."""
    user_email =serializers .CharField (source ='user.email',read_only =True )
    user_name =serializers .CharField (source ='user.full_name',read_only =True )

    class Meta :
        model =UserActivity 
        fields =[
        'id','user','user_email','user_name',
        'activity_type','description','ip_address',
        'metadata','timestamp',
        ]
        read_only_fields =fields 


class DashboardStatsSerializer (serializers .Serializer ):
    """Serializer for dashboard statistics."""
    # Comment_68
    total_users =serializers .IntegerField ()
    active_users =serializers .IntegerField ()
    users_by_role =serializers .DictField ()

    # Comment_69
    total_channels =serializers .IntegerField ()
    active_channels =serializers .IntegerField ()
    channels_by_type =serializers .DictField ()
    channels_by_priority =serializers .DictField ()

    # Comment_70
    total_patients =serializers .IntegerField ()
    new_patients_today =serializers .IntegerField ()
    new_patients_this_week =serializers .IntegerField ()

    # Comment_71
    total_medical_records =serializers .IntegerField ()
    critical_records =serializers .IntegerField ()

    # Comment_72
    security_alerts_today =serializers .IntegerField ()
    waf_blocks_today =serializers .IntegerField ()
    failed_logins_today =serializers .IntegerField ()
    biometric_logins_today =serializers .IntegerField ()

    # Comment_73
    activity_trend =serializers .ListField ()
    channels_trend =serializers .ListField ()
    patients_trend =serializers .ListField ()


class SecurityStatsSerializer (serializers .Serializer ):
    """Serializer for security statistics."""
    risk_score =serializers .IntegerField ()
    vulnerabilities_summary =serializers .DictField ()
    security_events_by_type =serializers .DictField ()
    security_events_trend =serializers .ListField ()
    top_blocked_ips =serializers .ListField ()
    port_scan_results =serializers .DictField ()
