"""
Serializers and Views for audit log.
"""
from rest_framework import serializers ,viewsets ,permissions ,filters 
from django_filters import rest_framework as django_filters 

from apps .audit .models import AuditLog
from apps .security .permissions import IsAdmin ,IsAuditor
from apps .core .net import get_client_ip


from rest_framework .decorators import action 
from rest_framework .response import Response 
from rest_framework .permissions import BasePermission
from django .http import HttpResponse 
import json 


class HasAuditView (BasePermission ):
    """بوابة audit.view الديناميكية (متطلب د. مجد — إدارة الصلاحيات).

    تُركَّب مع الأصناف الثابتة (IsAdmin | IsAuditor): الأدوار المسموحة
    تبقى كما هي، لكن سحب صلاحية audit.view من أي دور من صفحة إدارة
    الصلاحيات يمنعه من قراءة سجل التدقيق فوراً — والعكس، منحها لدور
    إضافي يفتحها له دون نشر كود.
    """
    message = 'لا تملك صلاحية عرض سجل التدقيق'

    def has_permission (self ,request ,view ):
        from apps .accounts .permissions import user_has_permission
        return user_has_permission (request .user ,'audit.view')

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
    # بوابة audit.view الديناميكية تحل محل IsAdmin|IsAuditor: افتراضيات
    # المصفوفة (SUPER_ADMIN/HOSPITAL_ADMIN/CENTER_ADMIN/AUDITOR) مطابقة
    # تماماً للأصناف الثابتة، مع إضافة المنح والسحب الديناميكي لكلا
    # الاتجاهين من صفحة إدارة الصلاحيات.
    permission_classes =[HasAuditView ]
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

        # The export itself is an auditable event: someone just pulled the whole
        # trail out of the system. get_client_ip, not REMOTE_ADDR — behind the
        # production proxy REMOTE_ADDR is the proxy's own address, so every export
        # was attributed to the load balancer and the row said nothing about who
        # took the data. AuditLog.save() signs this row like any other.
        AuditLog .objects .create (
        user =request .user ,
        event_type =AuditLog .EventType .DATA_EXPORT ,
        severity =AuditLog .Severity .INFO ,
        ip_address =get_client_ip (request ),
        details ={'exported_count':len (serializer .data ),'format':'json'}
        )
        return response 
