"""
Views for patients app.
"""
from rest_framework import viewsets ,permissions ,status 
from rest_framework .response import Response 
from rest_framework .decorators import action 
from django .core .exceptions import PermissionDenied 
from django .conf import settings 

from apps.patients.models import Patient, MedicalRecord
from apps.patients.serializers import PatientSerializer, MedicalRecordSerializer
from apps.audit.utils import log_security_event
from apps.core.mixins import PatientAccessMixin


class PatientViewSet(PatientAccessMixin, viewsets.ModelViewSet):
    """Patient management."""

    # Comment_241
    # Comment_242
    # Comment_243
    queryset =Patient .objects .select_related ('basin').order_by ('-created_at')
    serializer_class =PatientSerializer 

    def get_permissions (self ):
        if self .action in ['list','retrieve']:
            return [permissions .IsAuthenticated ()]
        return [permissions .IsAuthenticated ()]

    def get_queryset (self ):
        qs =super ().get_queryset ()
        # Comment_244
        from apps .basins .utils import basin_scoped_queryset 
        qs =basin_scoped_queryset (qs ,self .request .user ,lookup ='basin_id')
        # Comment_245
        basin_param =self .request .query_params .get ('basin')
        if basin_param :
            qs =qs .filter (basin_id =basin_param )
        return qs 

    def create (self ,request ,*args ,**kwargs ):
    # Comment_246
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
        # Comment_248
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
        # Comment_249
        viewable_channels = self.get_viewable_channels(user, patient)

            # Comment_250
        records =MedicalRecord .objects .filter (
        channel__in =viewable_channels 
        ).select_related ('channel','created_by').order_by ('-created_at')[:100 ]

        # Comment_251
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
        Aggregates the same permission-scoped data as `profile`, then calls
        the internal AI microservice (server-to-server, never exposed).
        The summary is generated from real record data only — the AI service
        is instructed to never invent clinical facts.
        """
        import json as _json
        import urllib.request

        patient = self.get_object()
        user = request.user
        self.check_patient_access(user, patient, 'AI summary')
        # Comment_252
        viewable_channels = self.get_viewable_channels(user, patient)

        records =MedicalRecord .objects .filter (
        channel__in =viewable_channels 
        ).select_related ('channel','created_by').order_by ('-created_at')[:40 ]

        # Comment_253
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

        # Comment_254
        ai_url =getattr (settings ,'AI_SERVICE_URL','http://127.0.0.1:8100')
        import requests
        try :
            resp = requests.post(
                f'{ai_url}/case-summary',
                json=payload,
                timeout=75
            )
            resp.raise_for_status()
            ai_data = resp.json()
        except Exception as e :# Comment_255
            log_security_event (
            user =user ,
            event_type ='AI_SUMMARY_FAILED',
            request =request ,
            details ={'patient_id':str (patient .id ),'error':str (e )[:200 ]},
            )
            return Response (
            {'detail':'تعذر توليد الملخص الذكي حالياً — تأكد من تشغيل خدمة الذكاء الاصطناعي'},
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
        'summary':ai_data .get ('summary',''),
        'generated_at':ai_data .get ('generated_at'),
        'records_used':len (payload ['records']),
        'disclaimer':'هذا الملخص مولّد آلياً ولا يُغني عن المراجعة الطبية البشرية',
        })


class MedicalRecordViewSet (viewsets .ModelViewSet ):
    """Medical records management."""

    # Comment_256
    # Comment_257
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

            # Comment_258
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

            # Comment_259
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


        # Comment_260
from django .db .models import Q 
