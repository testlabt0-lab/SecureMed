"""
Views for patients app.
"""
from rest_framework import viewsets ,permissions ,status
from rest_framework .response import Response
from rest_framework .decorators import action
from django .core .exceptions import PermissionDenied
from django .utils import timezone

from apps.patients.models import Patient, MedicalRecord
from apps.patients.serializers import PatientSerializer, MedicalRecordSerializer
from apps.audit.utils import log_security_event
from apps.core.mixins import PatientAccessMixin


class PatientViewSet(PatientAccessMixin, viewsets.ModelViewSet):
    """Patient management."""

    # select_related('basin'): PatientSerializer exposes basin_name via
    # basin.name — without the join each serialized row triggered an extra
    # DB round-trip to Neon (~20 extra queries per page over the WAN).
    queryset =Patient .objects .select_related ('basin').order_by ('-created_at')
    serializer_class =PatientSerializer 

    def get_permissions (self ):
        if self .action in ['list','retrieve']:
            return [permissions .IsAuthenticated ()]
        return [permissions .IsAuthenticated ()]

    def get_queryset (self ):
        qs =super ().get_queryset ()
        # Basin scoping (plan requirement: data is linked to basins)
        from apps .basins .utils import basin_scoped_queryset 
        qs =basin_scoped_queryset (qs ,self .request .user ,lookup ='basin_id')
        # Optional explicit basin filter: ?basin=<id>
        basin_param =self .request .query_params .get ('basin')
        if basin_param :
            qs =qs .filter (basin_id =basin_param )
        return qs 

    def create (self ,request ,*args ,**kwargs ):
    # Module activation by basin type (plan requirement)
        from apps .basins .utils import ensure_module_enabled 
        ensure_module_enabled (request .user ,'patients')
        return super ().create (request ,*args ,**kwargs )

    def retrieve(self, request, *args, **kwargs):
        patient = self.get_object()
        self.check_patient_access(request.user, patient, 'view')
        log_security_event(
        user =request .user ,
        event_type ='PATIENT_DATA_ACCESSED',
        request =request ,
        details ={'patient_id':str (patient .id )}
        )
        return super ().retrieve (request ,*args ,**kwargs )

    @action (detail =True ,methods =['get'])
    def channels(self, request, pk=None):
        """Get all channels for a patient."""
        patient = self.get_object()
        self.check_patient_access(request.user, patient, 'view channels')

        from apps .channels .models import Channel 
        from apps .channels .serializers import ChannelSerializer 

        channels = patient.channels.all()
        # Filter channels user can view
        viewable_channels = self.get_viewable_channels(request.user, patient)
        serializer = ChannelSerializer(
        viewable_channels ,many =True ,context ={'request':request }
        )
        return Response (serializer .data )

    @action (detail =True ,methods =['get'])
    def profile(self, request, pk=None):
        """
        Full patient profile: patient + medical records timeline +
        viewable channels + medical files (single aggregated response).
        """
        from django.db.models import Q
        from apps.channels.serializers import ChannelSerializer
        from apps.patients.serializers import MedicalRecordSerializer

        patient = self.get_object()
        user = request.user
        self.check_patient_access(user, patient, 'view profile')
        # Channels the requester can view for this patient
        viewable_channels = self.get_viewable_channels(user, patient)

            # Records belonging to those channels (access-scoped)
        records =MedicalRecord .objects .filter (
        channel__in =viewable_channels 
        ).select_related ('channel','created_by').order_by ('-created_at')[:100 ]

        # Medical files for those channels
        from apps .patients .models import MedicalFile 
        files =MedicalFile .objects .filter (
        channel__in =viewable_channels 
        ).order_by ('-created_at')[:50 ]

        log_security_event (
        user =user ,
        event_type ='PATIENT_DATA_ACCESSED',
        request =request ,
        details ={'patient_id':str (patient .id ),'view':'full_profile'}
        )

        return Response ({
        'patient':PatientSerializer (patient ).data ,
        'records':MedicalRecordSerializer (records ,many =True ).data ,
        'channels':ChannelSerializer (
        viewable_channels ,many =True ,context ={'request':request }
        ).data ,
        'files':[
        {
        'id':str (f .id ),
        'title':f .title ,
        'file_name':f .original_filename ,
        'file_type':f .file_type ,
        'file_type_display':f .get_file_type_display (),
        'file_size':f .file_size ,
        'is_critical':f .is_critical ,
        'uploaded_at':f .created_at ,
        }
        for f in files 
        ],
        'stats':{
        'total_records':records .count (),
        'total_channels':len (viewable_channels ),
        'total_files':len (files ),
        },
        })

    @action (detail =True ,methods =['post'],url_path ='ai-summary')
    def ai_summary(self, request, pk=None):
        """
        Generate an AI clinical case summary for this patient.

        Aggregates the same permission-scoped data as `profile`, then asks Gemini
        in-process — the same path as apps.ai.views. It used to POST this payload
        to a Node microservice at AI_SERVICE_URL (127.0.0.1:8100 by default):
        that service is not deployed alongside the app, so the endpoint answered
        503 anywhere but a developer laptop, and what it did send carried the
        patient's name, age and record text unmasked. The summary is built from
        real record data only, and the model is told never to invent a clinical
        fact.
        """
        import json as _json

        from apps.ai.utils import anonymize_patient_data
        from apps.ai.views import UPSTREAM_ERROR, get_gemini_model
        from apps.basins.utils import ensure_module_enabled

        patient = self.get_object()
        user = request.user
        self.check_patient_access(user, patient, 'AI summary')
        ensure_module_enabled(user, 'ai_assistant')
        # Same access-scoping as the profile action
        viewable_channels = self.get_viewable_channels(user, patient)

        records =MedicalRecord .objects .filter (
        channel__in =viewable_channels 
        ).select_related ('channel','created_by').order_by ('-created_at')[:40 ]

        # ---- Build the AI payload (permission-scoped) ----
        payload ={
        'patient':{
        'full_name':patient .full_name ,
        'gender':patient .gender ,
        'age':patient .age ,
        'blood_type':patient .blood_type ,
        'allergies':patient .allergies ,
        'chronic_conditions':patient .chronic_conditions ,
        },
        'channels':[
        {
        'name':c .name ,
        'channel_type':c .channel_type ,
        'priority':c .priority ,
        'status':c .status ,
        }
        for c in viewable_channels [:10 ]
        ],
        'records':[
        {
        'record_type':r .record_type ,
        'title':r .title ,
        'content':(r .content or '')[:800 ],
        'is_critical':r .is_critical ,
        'created_at':r .created_at .isoformat (),
        }
        for r in records 
        ],
        'meta':{
        'record_count':records .count (),
        'generated_for_role':user .role ,
        },
        }

        # ---- Call the AI microservice (server-to-server) ----
        model =get_gemini_model ()
        if not model :
            log_security_event (
            user =user ,
            event_type ='AI_SUMMARY_FAILED',
            request =request ,
            details ={'patient_id':str (patient .id ),'error':'GEMINI_API_KEY not configured'},
            )
            return Response (
            {'detail':UPSTREAM_ERROR },
            status =status .HTTP_503_SERVICE_UNAVAILABLE ,
            )

        try :
            # Anonymised for the same reason every other call in apps.ai is: the
            # payload leaves the deployment, and the clinical content is what the
            # model needs — the patient's identity is not.
            safe_payload =anonymize_patient_data (payload )
            prompt =(
            'أنت طبيب استشاري. اكتب ملخصاً سريرياً موجزاً باللغة العربية لهذه '
            'الحالة، معتمداً على البيانات المرفقة فقط، ولا تخترع أي معلومة طبية '
            'غير موجودة فيها.\n\n'
            f'{_json .dumps (safe_payload ,ensure_ascii =False ,default =str )}'
            )
            response =model .generate_content (prompt )
            summary =response .text
        except Exception as e :# service down / timeout / bad response
            # str(e) from the SDK can carry the request URL and, on an auth
            # error, part of the API key — the client gets the module's generic
            # message and the real error goes to the audit trail.
            log_security_event (
            user =user ,
            event_type ='AI_SUMMARY_FAILED',
            request =request ,
            details ={'patient_id':str (patient .id ),'error':str (e )[:200 ]},
            )
            return Response (
            {'detail':UPSTREAM_ERROR },
            status =status .HTTP_503_SERVICE_UNAVAILABLE ,
            )
        log_security_event (
        user =user ,
        event_type ='AI_SUMMARY_GENERATED',
        request =request ,
        details ={
        'patient_id':str (patient .id ),
        'records_used':len (payload ['records']),
        'channels_used':len (payload ['channels']),
        },
        )

        return Response ({
        'summary':summary ,
        'generated_at':timezone .now ().isoformat (),
        'records_used':len (payload ['records']),
        'disclaimer':'هذا الملخص مولّد آلياً ولا يُغني عن المراجعة الطبية البشرية',
        })


class MedicalRecordViewSet (viewsets .ModelViewSet ):
    """Medical records management."""

    # select_related: serializer reads channel.name + created_by.full_name
    # per row — avoid 2 extra queries per record on list responses.
    queryset =MedicalRecord .objects .select_related (
    'channel','created_by'
    ).order_by ('-created_at')
    serializer_class =MedicalRecordSerializer 

    def get_queryset (self ):
        """Filter records by user's accessible channels."""
        from django .db .models import Q 
        user =self .request .user 
        if user .role in ['SUPER_ADMIN','HOSPITAL_ADMIN']:
            return MedicalRecord .objects .select_related (
            'channel','created_by'
            ).order_by ('-created_at')

            # Get channels the user can view
        from apps .channels .models import Channel 
        accessible_channels =Channel .objects .filter (
        Q (owner =user )|Q (memberships__user =user ,memberships__is_active =True )
        )
        return MedicalRecord .objects .filter (
        channel__in =accessible_channels 
        ).select_related ('channel','created_by').order_by ('-created_at')

    def perform_create (self ,serializer ):
        """Create record - check user has permission in channel."""
        channel =serializer .validated_data ['channel']
        if not channel .can_view (self .request .user ):
            raise PermissionDenied ('غير مصرح لك بإضافة سجلات لهذه القناة')

            # Check if user can create records (must be admin or EDITOR or higher)
        if self .request .user .role not in ['SUPER_ADMIN','HOSPITAL_ADMIN']:
            role =channel .get_user_role (self .request .user )
            if role not in ['OWNER','MODERATOR','EDITOR','CONTRIBUTOR']:
                raise PermissionDenied ('دورك لا يسمح بإنشاء سجلات')

        record =serializer .save ()
        log_security_event (
        user =self .request .user ,
        event_type ='MEDICAL_RECORD_CREATED',
        request =self .request ,
        details ={
        'record_id':str (record .id ),
        'channel_id':str (channel .id ),
        'record_type':record .record_type ,
        }
        )


        # Helper import
from django .db .models import Q 
