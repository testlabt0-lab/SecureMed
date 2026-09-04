"""
Telemedicine views.
"""
from django .utils import timezone 
from rest_framework import viewsets ,status ,permissions 
from rest_framework .decorators import action 
from rest_framework .response import Response 

from .models import Consultation ,ChatMessage 
from .serializers import (
ConsultationSerializer ,
ConsultationCreateSerializer ,
ChatMessageSerializer ,
)

class ConsultationViewSet (viewsets .ModelViewSet ):
    """CRUD for Telemedicine Consultations."""
    queryset =Consultation .objects .select_related ('patient','doctor').prefetch_related ('messages__sender').all ()
    permission_classes =[permissions .IsAuthenticated ]
    ordering =['-scheduled_time']

    def get_serializer_class (self ):
        if self .action =='create':
            return ConsultationCreateSerializer 
        return ConsultationSerializer 

    def get_queryset (self ):
        qs =super ().get_queryset ()
        user =self .request .user 

        # Comment_416
        if user .role =='PATIENT':
        # Comment_417
            pass 
        elif user .role =='DOCTOR':
            qs =qs .filter (doctor =user )

        status_filter =self .request .query_params .get ('status')
        if status_filter :
            qs =qs .filter (status =status_filter )

        return qs 

    @action (detail =True ,methods =['post'])
    def join (self ,request ,pk =None ):
        """Mark consultation as in progress."""
        consultation =self .get_object ()
        if consultation .status =='SCHEDULED':
            consultation .status ='IN_PROGRESS'
            consultation .started_at =timezone .now ()
            consultation .save (update_fields =['status','started_at'])

            # Comment_418
            # Comment_419
        return Response (ConsultationSerializer (consultation ).data )

    @action (detail =True ,methods =['post'])
    def complete (self ,request ,pk =None ):
        """End the consultation."""
        consultation =self .get_object ()
        consultation .status ='COMPLETED'
        consultation .ended_at =timezone .now ()

        notes =request .data .get ('notes','')
        diagnosis =request .data .get ('diagnosis','')
        if notes :
            consultation .notes =notes 
        if diagnosis :
            consultation .diagnosis =diagnosis 

        consultation .save (update_fields =['status','ended_at','notes','diagnosis'])
        return Response (ConsultationSerializer (consultation ).data )


class ChatMessageViewSet (viewsets .ModelViewSet ):
    """CRUD for Consultation Chat Messages."""
    queryset =ChatMessage .objects .select_related ('sender').all ()
    serializer_class =ChatMessageSerializer 
    permission_classes =[permissions .IsAuthenticated ]
    ordering =['created_at']

    def get_queryset (self ):
        qs =super ().get_queryset ()
        consultation_id =self .request .query_params .get ('consultation')
        if consultation_id :
            qs =qs .filter (consultation_id =consultation_id )
        return qs 

    def perform_create (self ,serializer ):
        serializer .save (sender =self .request .user )
