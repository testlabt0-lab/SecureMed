"""
Views for the basins app.

Permission model:
  * Any authenticated user can LIST/RETRIEVE basins (needed for dropdowns).
  * Only SUPER_ADMIN can create/update/delete basins or toggle modules.
  * HOSPITAL_ADMIN sees basin-scoped queries elsewhere (users/patients/channels).
"""
from rest_framework import status ,viewsets ,permissions 
from rest_framework .decorators import action 
from rest_framework .response import Response 

from apps .basins .models import Basin 
from apps .basins .serializers import BasinSerializer ,BasinStatsSerializer 
from apps .audit .utils import log_security_event 


class IsSuperAdmin (permissions .BasePermission ):
    """Write operations are reserved to SUPER_ADMIN."""

    def has_permission (self ,request ,view ):
        if request .method in permissions .SAFE_METHODS :
            return request .user and request .user .is_authenticated 
        return (
        request .user and request .user .is_authenticated 
        and request .user .role =='SUPER_ADMIN'
        )


class BasinViewSet (viewsets .ModelViewSet ):
    """CRUD + module-activation actions for health basins."""

    queryset =Basin .objects .all ().order_by ('name')
    serializer_class =BasinSerializer 
    permission_classes =[IsSuperAdmin ]
    filterset_fields =['basin_type','is_active','governorate']
    search_fields =['name','code','governorate','directorate']

    def perform_create (self ,serializer ):
        basin =serializer .save ()
        log_security_event (
        user =self .request .user ,
        event_type ='BASIN_CREATED',
        request =self .request ,
        details ={'basin':basin .name ,'type':basin .basin_type },
        )

    def perform_update (self ,serializer ):
        basin =serializer .save ()
        log_security_event (
        user =self .request .user ,
        event_type ='BASIN_UPDATED',
        request =self .request ,
        details ={'basin':basin .name },
        )

    def perform_destroy (self ,instance ):
        if instance .stats ()['users']>0 :
        # Comment_174
            raise permissions .exceptions .PermissionDenied (
            'لا يمكن حذف حوض مرتبط بمستخدمين — عطّله بدلاً من ذلك'
            )
        log_security_event (
        user =self .request .user ,
        event_type ='BASIN_DELETED',
        request =self .request ,
        details ={'basin':instance .name },
        )
        instance .delete ()

        # Comment_175
    @action (detail =False ,methods =['get'])
    def modules (self ,request ):
        """Catalogue of all system modules (for the admin UI)."""
        return Response ([
        {'key':m ,'label':str (Basin .MODULE_LABELS .get (m ,m ))}
        for m in Basin .ALL_MODULES 
        ])

    @action (detail =False ,methods =['get'])
    def my_basin (self ,request ):
        """The basin of the current user (for UI headers / gating)."""
        basin =request .user .basin 
        if not basin :
            return Response ({'basin':None })
        return Response ({'basin':BasinSerializer (basin ).data })

    @action (detail =True ,methods =['post'])
    def toggle_module (self ,request ,pk =None ):
        """POST {module, enabled} — enable/disable one module in this basin."""
        basin =self .get_object ()
        module =str (request .data .get ('module')or '')
        enabled =bool (request .data .get ('enabled'))
        if module not in Basin .ALL_MODULES :
            return Response (
            {'detail':'وحدة غير معروفة'},
            status =status .HTTP_400_BAD_REQUEST ,
            )
        if enabled :
            basin .enable_module (module )
        else :
            basin .disable_module (module )
        log_security_event (
        user =request .user ,
        event_type ='BASIN_MODULE_TOGGLED',
        request =request ,
        details ={'basin':basin .name ,'module':module ,'enabled':enabled },
        )
        return Response ({
        'detail':'تم التفعيل'if enabled else 'تم التعطيل',
        'enabled_modules':basin .enabled_modules ,
        })

    @action (detail =True ,methods =['post'])
    def apply_type_defaults (self ,request ,pk =None ):
        """POST {} — re-activate default modules for the basin's TYPE."""
        basin =self .get_object ()
        new_type =request .data .get ('basin_type')
        if new_type :
            if new_type not in Basin .BasinType .values :
                return Response (
                {'detail':'نوع حوض غير صالح'},
                status =status .HTTP_400_BAD_REQUEST ,
                )
            basin .basin_type =new_type 
            basin .save (update_fields =['basin_type','updated_at'])
        modules =basin .apply_default_modules ()
        log_security_event (
        user =request .user ,
        event_type ='BASIN_TYPE_DEFAULTS_APPLIED',
        request =request ,
        details ={'basin':basin .name ,'type':basin .basin_type },
        )
        return Response ({
        'detail':'تم تفعيل الوحدات الافتراضية حسب نوع الحوض',
        'basin_type':basin .basin_type ,
        'enabled_modules':modules ,
        })

    @action (detail =False ,methods =['get'])
    def overview (self ,request ):
        """System-wide basin statistics (admin dashboard)."""
        from django .db .models import Count 
        by_type_rows =Basin .objects .values ('basin_type').annotate (
        count =Count ('id')
        )
        by_type ={row ['basin_type']:row ['count']for row in by_type_rows }
        data ={
        'total':Basin .objects .count (),
        'active':Basin .objects .filter (is_active =True ).count (),
        'by_type':by_type ,
        }
        return Response (BasinStatsSerializer (data ).data )
