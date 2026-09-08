"""
Medical File serializer and views.
"""
import os
from rest_framework import serializers ,viewsets ,permissions ,status
from rest_framework .decorators import action
from rest_framework .response import Response
from django .db .models import Q
from django .http import FileResponse
from django .core .exceptions import PermissionDenied
from django .urls import reverse

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
        # Accepted on upload, never echoed back: a ModelSerializer FileField renders
        # as obj.file.url, which would put the raw /media/ path in the response right
        # next to the file_url that exists precisely to avoid it. Done with
        # extra_kwargs rather than by redeclaring the field, so DRF still builds it
        # from the model and keeps validate_file_extension / validate_file_size —
        # redeclaring it as serializers.FileField() would silently drop both.
        # Validation errors stay keyed 'file', which is what the upload form in
        # ChannelDetail.tsx reads.
        extra_kwargs ={'file':{'write_only':True }}

    def get_file_url (self ,obj ):
        """URL of the authenticated download endpoint — never a raw /media/ path.

        This used to return ``request.build_absolute_uri(obj.file.url)``, i.e. a
        ``/media/medical_files/<channel>/<uuid>.pdf`` URL, and that value is what the
        SPA renders into links and image tags. Two problems: whether that URL is
        authorised at all depends on how ``config/urls.py`` happens to be routing
        MEDIA_URL, and the raw path leaks into browser history, referrers and server
        logs. Pointing at the DRF action instead means every read goes through
        permission checks and lands in the audit trail, and it keeps working
        unchanged if media later moves to S3.
        """
        request =self .context .get ('request')
        if not (request and obj .file and obj .channel .can_view (request .user )):
            return None
        return request .build_absolute_uri (
        reverse ('medical-file-download',kwargs ={'pk':obj .pk })
        )


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

            # Check if user has upload permission (EDITOR or higher)
        role =channel .get_user_role (self .request .user )
        if role not in ['OWNER','MODERATOR','EDITOR','CONTRIBUTOR']:
            raise PermissionDenied ('دورك لا يسمح برفع الملفات')

            # Get original filename
        file =serializer .validated_data .get ('file')
        original_filename =file .name if file else serializer .validated_data .get ('original_filename','')

        file_obj =serializer .save (
        uploaded_by =self .request .user ,
        original_filename =original_filename ,
        )

        # Log the upload
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

        # Notify channel members
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

        # Check access permission
        if not instance .channel .can_view (request .user ):
            raise PermissionDenied ('غير مصرح لك بالوصول إلى هذا الملف')

            # Record access
        instance .record_access (request .user )

        from apps .core .anomaly import record_phi_access
        record_phi_access (request .user ,resource ='medical_file',path =instance .file .name )

        # Log access
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

        # Check access permission
        if not instance .channel .can_view (request .user ):
            raise PermissionDenied ('غير مصرح لك بتنزيل هذا الملف')

            # Record access
        instance .record_access (request .user )

        from apps .core .anomaly import record_phi_access
        record_phi_access (request .user ,resource ='medical_file',path =instance .file .name )

        # Log download
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

        # Opened through the storage API, which decrypts transparently — see
        # apps.core.storage. Content-Length is set by FileResponse from the decrypted
        # stream, and EncryptedFileSystemStorage.size() reports the plaintext length,
        # so neither is inflated by the ciphertext header.
        #
        # `filename=` rather than a hand-built Content-Disposition: the previous
        # f'attachment; filename="{original_filename}"' interpolated a user-supplied
        # name straight into a header — a quote in the name broke the header, and an
        # Arabic name became either mojibake or a stripped-to-nothing filename.
        # FileResponse emits RFC 5987 `filename*=utf-8''…` alongside an ASCII
        # fallback, which is what actually makes Arabic filenames survive.
        response =FileResponse (
        instance .file .open ('rb'),
        content_type =instance .mime_type or 'application/octet-stream',
        as_attachment =True ,
        filename =instance .original_filename or os .path .basename (instance .file .name ),
        )
        # This endpoint always downloads, so nothing here is rendered — but PHI must
        # still stay out of shared caches, and nosniff keeps a browser from deciding
        # for itself that a mislabelled payload is HTML.
        response ['X-Content-Type-Options']='nosniff'
        response ['Cache-Control']='private, no-store, max-age=0'
        response ['Referrer-Policy']='no-referrer'
        return response
