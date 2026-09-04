"""
Serializers and Views for audit log.
"""
from rest_framework import serializers ,viewsets ,permissions ,filters 
from django_filters import rest_framework as django_filters 

from apps .audit .models import AuditLog 
from apps .security .permissions import IsAdmin ,IsAuditor 


from rest_framework .decorators import action 
from rest_framework .response import Response 
from django .http import HttpResponse 
import json 

class AuditLogSerializer (serializers .ModelSerializer ):
    """Serializer for AuditLog."""

    user_email =serializers .CharField (source ='user.email',read_only =True )
    user_name =serializers .CharField (source ='user.full_name',read_only =True )
    event_type_display =serializers .CharField (
    source ='get_event_type_display',read_only =True 
    )
    severity_display =serializers .CharField (
    source ='get_severity_display',read_only =True 
    )

    class Meta :
        model =AuditLog 
        fields =[
        'id','user','user_email','user_name',
        'event_type','event_type_display',
        'severity','severity_display',
        'ip_address','user_agent','path','method',
        'mac_address','device_fingerprint','hostname',
        'os_info','browser_info','session_id','geo_location','risk_score',
        'details','timestamp',
        ]
        read_only_fields =fields 


class AuditLogFilter (django_filters .FilterSet ):
    """Filter for audit logs."""

    class Meta :
        model =AuditLog 
        fields ={
        'event_type':['exact'],
        'severity':['exact'],
        'user':['exact'],
        'timestamp':['date','gte','lte'],
        }


class AuditLogViewSet (viewsets .ReadOnlyModelViewSet ):
    """View audit logs (admin/auditor only)."""
    queryset =AuditLog .objects .all ().order_by ('-timestamp')
    serializer_class =AuditLogSerializer 
    permission_classes =[IsAdmin |IsAuditor ]
    filterset_class =AuditLogFilter 
    search_fields =['user__email','user__full_name','path','ip_address','mac_address']
    ordering_fields =['timestamp','severity','event_type','risk_score']

    @action (detail =False ,methods =['get'])
    def export (self ,request ):
        """Export audit logs as JSON for SIEM integration."""
        queryset =self .filter_queryset (self .get_queryset ())
        serializer =self .get_serializer (queryset ,many =True )
        response =HttpResponse (
        json .dumps (serializer .data ,ensure_ascii =False ,indent =2 ),
        content_type ='application/json'
        )
        response ['Content-Disposition']='attachment; filename="audit_logs_export.json"'

        # Comment_141
        AuditLog .objects .create (
        user =request .user ,
        event_type =AuditLog .EventType .DATA_EXPORT ,
        severity =AuditLog .Severity .INFO ,
        ip_address =request .META .get ('REMOTE_ADDR'),
        details ={'exported_count':queryset .count (),'format':'json'}
        )
        return response 
