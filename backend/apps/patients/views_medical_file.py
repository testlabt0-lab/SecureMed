"""
Medical File serializer and views.
"""
import os 
from rest_framework import serializers ,viewsets ,permissions ,status 
from rest_framework .decorators import action 
from rest_framework .response import Response 
from django .http import FileResponse 
from django .core .exceptions import PermissionDenied 

from apps .patients .models import MedicalFile 
from apps .audit .utils import log_security_event 
from apps .notifications .utils import notify_channel_members 


class MedicalFileSerializer (serializers .ModelSerializer ):
    """Serializer for MedicalFile."""
    uploaded_by_name =serializers .CharField (source ='uploaded_by.full_name',read_only =True )
    file_type_display =serializers .CharField (source ='get_file_type_display',read_only =True )
    file_url =serializers .SerializerMethodField ()

    class Meta :
        model =MedicalFile 
        fields =[
        'id','channel','patient','uploaded_by','uploaded_by_name',
        'file','file_url','original_filename','file_type','file_type_display',
        'file_size','mime_type','title','description',
        'study_date','body_part','modality','is_critical',
        'access_count','last_accessed',
        'created_at','updated_at',
        ]
        read_only_fields =[
        'id','uploaded_by','file_size','mime_type',
        'access_count','last_accessed','created_at','updated_at',
        ]

    def get_file_url (self ,obj ):
        """Get file URL (only if user has access)."""
        request =self .context .get ('request')
        if request and obj .channel .can_view (request .user ):
            return request .build_absolute_uri (obj .file .url )if obj .file else None 
        return None 


class MedicalFileViewSet (viewsets .ModelViewSet ):
    """
    Medical File management.
    Files are access-controlled based on channel membership.
    """
    serializer_class =MedicalFileSerializer 
    permission_classes =[permissions .IsAuthenticated ]
    filterset_fields =['channel','patient','file_type','is_critical']
    search_fields =['title','description','original_filename']
    ordering_fields =['created_at','file_size','access_count']
    ordering =['-created_at']

    def get_queryset (self ):
        """Only return files from channels the user can access."""
        user =self .request .user 
        if user .role in ['SUPER_ADMIN','HOSPITAL_ADMIN']:
            return MedicalFile .objects .all ()

        from apps .channels .models import Channel 
        accessible_channels =Channel .objects .filter (
        Q (owner =user )|Q (memberships__user =user ,memberships__is_active =True )
        )
        return MedicalFile .objects .filter (channel__in =accessible_channels ).distinct ()

    def perform_create (self ,serializer ):
        """Create medical file - check permissions."""
        channel =serializer .validated_data ['channel']
        if not channel .can_view (self .request .user ):
            raise PermissionDenied ('غير مصرح لك برفع ملفات في هذه القناة')

            # Comment_261
        role =channel .get_user_role (self .request .user )
        if role not in ['OWNER','MODERATOR','EDITOR','CONTRIBUTOR']:
            raise PermissionDenied ('دورك لا يسمح برفع الملفات')

            # Comment_262
        file =serializer .validated_data .get ('file')
        original_filename =file .name if file else serializer .validated_data .get ('original_filename','')

        file_obj =serializer .save (
        uploaded_by =self .request .user ,
        original_filename =original_filename ,
        )

        # Comment_263
        log_security_event (
        user =self .request .user ,
        event_type ='PATIENT_DATA_ACCESSED',
        request =self .request ,
        details ={
        'action':'file_upload',
        'file_id':str (file_obj .id ),
        'channel_id':str (channel .id ),
        'file_type':file_obj .file_type ,
        'file_size':file_obj .file_size ,
        }
        )

        # Comment_264
        notify_channel_members (
        channel =channel ,
        notification_type ='NEW_MEDICAL_RECORD',
        title =f'ملف طبي جديد: {file_obj .title }',
        message =f'تم رفع ملف {file_obj .get_file_type_display ()} بواسطة {self .request .user .full_name }',
        sender =self .request .user ,
        data ={'file_id':str (file_obj .id ),'file_type':file_obj .file_type },
        )

    def retrieve (self ,request ,*args ,**kwargs ):
        """Retrieve file - record access."""
        instance =self .get_object ()

        # Comment_265
        if not instance .channel .can_view (request .user ):
            raise PermissionDenied ('غير مصرح لك بالوصول إلى هذا الملف')

            # Comment_266
        instance .record_access (request .user )

        # Comment_267
        log_security_event (
        user =request .user ,
        event_type ='PATIENT_DATA_ACCESSED',
        request =request ,
        details ={
        'action':'file_view',
        'file_id':str (instance .id ),
        'channel_id':str (instance .channel .id ),
        }
        )

        return super ().retrieve (request ,*args ,**kwargs )

    @action (detail =True ,methods =['get'])
    def download (self ,request ,pk =None ):
        """Download the medical file."""
        instance =self .get_object ()

        # Comment_268
        if not instance .channel .can_view (request .user ):
            raise PermissionDenied ('غير مصرح لك بتنزيل هذا الملف')

            # Comment_269
        instance .record_access (request .user )

        # Comment_270
        log_security_event (
        user =request .user ,
        event_type ='PATIENT_DATA_ACCESSED',
        request =request ,
        details ={
        'action':'file_download',
        'file_id':str (instance .id ),
        'channel_id':str (instance .channel .id ),
        }
        )

        # Comment_271
        response =FileResponse (
        instance .file .open ('rb'),
        content_type =instance .mime_type or 'application/octet-stream',
        )
        response ['Content-Disposition']=f'attachment; filename="{instance .original_filename }"'
        return response 


        # Comment_272
from django .db .models import Q 
