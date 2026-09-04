from rest_framework import viewsets ,permissions ,status 
from rest_framework .response import Response 
from rest_framework .decorators import action 
from django .utils import timezone 
from apps .security .models import DeviceRegistry ,BlockedDevice ,BlockedIP ,LoginHistory 
from apps .security .permissions import IsAdmin ,IsAuditor 
from rest_framework import serializers 

class DeviceRegistrySerializer (serializers .ModelSerializer ):
    class Meta :
        model =DeviceRegistry 
        fields ='__all__'

class BlockedDeviceSerializer (serializers .ModelSerializer ):
    class Meta :
        model =BlockedDevice 
        fields ='__all__'
        read_only_fields =['blocked_by','created_at']

class BlockedIPSerializer (serializers .ModelSerializer ):
    class Meta :
        model =BlockedIP 
        fields ='__all__'

class LoginHistorySerializer (serializers .ModelSerializer ):
    user_email =serializers .CharField (source ='user.email',read_only =True )
    class Meta :
        model =LoginHistory 
        fields ='__all__'


class DeviceRegistryViewSet (viewsets .ReadOnlyModelViewSet ):
    """View devices registered to users."""
    serializer_class =DeviceRegistrySerializer 
    permission_classes =[permissions .IsAuthenticated ]

    def get_queryset (self ):
        user =self .request .user 
        if user .role in ['SUPER_ADMIN','HOSPITAL_ADMIN','AUDITOR']:
            return DeviceRegistry .objects .all ().order_by ('-last_login')
        return DeviceRegistry .objects .filter (user =user ).order_by ('-last_login')

    @action (detail =True ,methods =['post'])
    def trust (self ,request ,pk =None ):
        """Mark a device as trusted (requires auth)."""
        device =self .get_object ()
        if device .user !=request .user and request .user .role not in ['SUPER_ADMIN','HOSPITAL_ADMIN']:
            return Response ({'detail':'غير مصرح'},status =status .HTTP_403_FORBIDDEN )

        device .is_trusted =True 
        device .save (update_fields =['is_trusted'])
        return Response ({'detail':'تم تعيين الجهاز كموثوق'})

    @action (detail =True ,methods =['post'])
    def activate_module (self ,request ,pk =None ):
        """Activate a module for a device (plan requirement: تفعيل الخدمات الوهمية)."""
        device =self .get_object ()
        module =request .data .get ('module')
        if not module :
            return Response (
            {'detail':'اسم-module مطلوب'},
            status =status .HTTP_400_BAD_REQUEST ,
            )

            # Comment_310
        from apps .basins .utils import ensure_module_enabled 
        ensure_module_enabled (request .user ,f'device_{module }')

        current_modules =device .modules_activated if isinstance (device .modules_activated ,list )else []
        if module not in current_modules :
            current_modules .append (module )
            device .modules_activated =current_modules 
            device .save (update_fields =['modules_activated'])

        return Response ({
        'detail':f'تم تفعيل الخدمة {module } للجهاز بنجاح',
        'module':module ,
        'modules_activated':device .modules_activated ,
        })

    @action (detail =False ,methods =['get'])
    def types (self ,request ):
        """Get device types detected from fingerprints."""
        from apps .security .middleware import WAFMiddleware 
        middleware =WAFMiddleware (lambda r :None )
        device_type_counts ={}

        queryset =self .get_queryset ()
        for device in queryset :
            if device .device_fingerprint :
                device_type =middleware ._detect_device_type (device .device_fingerprint )
                device_type_counts [device_type ]=device_type_counts .get (device_type ,0 )+1 

        return Response (device_type_counts )


class BlockedDeviceViewSet (viewsets .ModelViewSet ):
    """Manage blocked devices (admin/auditor only)."""
    queryset =BlockedDevice .objects .all ().order_by ('-created_at')
    serializer_class =BlockedDeviceSerializer 
    permission_classes =[IsAdmin |IsAuditor ]

    def perform_create (self ,serializer ):
        serializer .save (blocked_by =self .request .user )

    @action (detail =True ,methods =['post'])
    def unblock (self ,request ,pk =None ):
        """Unblock a device."""
        device =self .get_object ()
        device .is_active =False 
        device .save (update_fields =['is_active'])
        
        if device.device_fingerprint:
            from django.core.cache import cache
            cache.delete(f"blocked_device_{device.device_fingerprint}")
            cache.delete(f"failed_login_level_{device.device_fingerprint}")
            cache.delete(f"failed_login_device_{device.device_fingerprint}")
            
        return Response ({'detail':'تم إلغاء حظر الجهاز'})


class BlockedIPViewSet (viewsets .ModelViewSet ):
    """Manage blocked IPs (admin/auditor only)."""
    queryset =BlockedIP .objects .all ().order_by ('-created_at')
    serializer_class =BlockedIPSerializer 
    permission_classes =[IsAdmin |IsAuditor ]

    @action (detail =True ,methods =['post'])
    def unblock (self ,request ,pk =None ):
        """Unblock an IP."""
        blocked_ip =self .get_object ()
        blocked_ip .is_active =False 
        blocked_ip .save (update_fields =['is_active'])
        return Response ({'detail':'تم إلغاء حظر عنوان IP'})


class LoginHistoryViewSet (viewsets .ReadOnlyModelViewSet ):
    """View detailed login history."""
    serializer_class =LoginHistorySerializer 
    permission_classes =[permissions .IsAuthenticated ]

    def get_queryset (self ):
        user =self .request .user 
        if user .role in ['SUPER_ADMIN','HOSPITAL_ADMIN','AUDITOR']:
            return LoginHistory .objects .all ().order_by ('-timestamp')
        return LoginHistory .objects .filter (user =user ).order_by ('-timestamp')
