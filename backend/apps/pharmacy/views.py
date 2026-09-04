"""
Pharmacy views — Full CRUD for medications, prescriptions, stock management,
drug interaction checking, and pharmacy statistics.
"""
from datetime import timedelta 

from django .db .models import F ,Sum ,Count ,Q 
from django .utils import timezone 
from rest_framework import viewsets ,status ,permissions 
from rest_framework .decorators import action 
from rest_framework .response import Response 

from apps .audit .utils import log_security_event 

from .models import Medication ,DrugInteraction ,Prescription ,PrescriptionItem 
from .serializers import (
MedicationSerializer ,
DrugInteractionSerializer ,
PrescriptionSerializer ,
PrescriptionCreateSerializer ,
PrescriptionItemSerializer ,
StockMovementSerializer ,
DispensePrescriptionSerializer ,
)


class MedicationViewSet (viewsets .ModelViewSet ):
    """Full CRUD for the medication inventory."""
    queryset =Medication .objects .all ()
    serializer_class =MedicationSerializer 
    permission_classes =[permissions .IsAuthenticated ]
    search_fields =['name','scientific_name','barcode']
    ordering_fields =['name','stock_quantity','expiry_date','unit_price']
    ordering =['name']

    def get_queryset (self ):
        qs =super ().get_queryset ()
        # Comment_278
        search =self .request .query_params .get ('search','')
        if search :
            qs =qs .filter (
            Q (name__icontains =search )|
            Q (scientific_name__icontains =search )|
            Q (barcode__icontains =search )
            )
        stock_filter =self .request .query_params .get ('stock_status')
        if stock_filter =='low':
            qs =qs .filter (stock_quantity__lte =F ('reorder_level'))
        elif stock_filter =='out':
            qs =qs .filter (stock_quantity =0 )
        active =self .request .query_params .get ('active')
        if active =='true':
            qs =qs .filter (is_active =True )
        elif active =='false':
            qs =qs .filter (is_active =False )
        return qs 

    @action (detail =False ,methods =['get'])
    def low_stock (self ,request ):
        """Medications at or below reorder level."""
        meds =self .get_queryset ().filter (
        stock_quantity__lte =F ('reorder_level'),is_active =True 
        )
        serializer =self .get_serializer (meds ,many =True )
        return Response (serializer .data )

    @action (detail =False ,methods =['get'])
    def expired (self ,request ):
        """Medications past expiry date."""
        meds =self .get_queryset ().filter (
        expiry_date__lt =timezone .now ().date (),is_active =True 
        )
        serializer =self .get_serializer (meds ,many =True )
        return Response (serializer .data )

    @action (detail =False ,methods =['get'])
    def expiring_soon (self ,request ):
        """Medications expiring in the next 30 days."""
        cutoff =timezone .now ().date ()+timedelta (days =30 )
        meds =self .get_queryset ().filter (
        expiry_date__lte =cutoff ,
        expiry_date__gte =timezone .now ().date (),
        is_active =True ,
        )
        serializer =self .get_serializer (meds ,many =True )
        return Response (serializer .data )

    @action (detail =True ,methods =['post'])
    def adjust_stock (self ,request ,pk =None ):
        """Adjust stock quantity (IN/OUT/ADJUSTMENT/RETURN)."""
        medication =self .get_object ()
        serializer =StockMovementSerializer (data =request .data )
        serializer .is_valid (raise_exception =True )
        d =serializer .validated_data 

        qty =d ['quantity']
        movement =d ['movement_type']
        reason =d .get ('reason','')

        if movement =='IN'or movement =='RETURN':
            medication .stock_quantity +=qty 
        elif movement =='OUT':
            if medication .stock_quantity <qty :
                return Response (
                {'detail':f'الكمية المتوفرة ({medication .stock_quantity }) أقل من المطلوبة ({qty })'},
                status =status .HTTP_400_BAD_REQUEST ,
                )
            medication .stock_quantity -=qty 
        else :# Comment_279
            medication .stock_quantity =qty 

        medication .save (update_fields =['stock_quantity'])

        log_security_event (
        user =request .user ,
        event_type ='PHARMACY_STOCK_CHANGE',
        request =request ,
        details ={
        'medication':medication .name ,
        'type':movement ,
        'qty':qty ,
        'new_stock':medication .stock_quantity ,
        'reason':reason ,
        },
        )

        return Response (self .get_serializer (medication ).data )


class DrugInteractionViewSet (viewsets .ModelViewSet ):
    """Manage drug interaction rules."""
    queryset =DrugInteraction .objects .select_related ('drug_a','drug_b').all ()
    serializer_class =DrugInteractionSerializer 
    permission_classes =[permissions .IsAuthenticated ]

    @action (detail =False ,methods =['post'])
    def check (self ,request ):
        """Check interactions between a list of medication IDs."""
        medication_ids =request .data .get ('medication_ids',[])
        if len (medication_ids )<2 :
            return Response ({'interactions':[],'has_severe':False })

        interactions =DrugInteraction .objects .filter (
        Q (drug_a_id__in =medication_ids ,drug_b_id__in =medication_ids )
        ).select_related ('drug_a','drug_b')

        serializer =self .get_serializer (interactions ,many =True )
        has_severe =interactions .filter (severity ='SEVERE').exists ()

        return Response ({
        'interactions':serializer .data ,
        'has_severe':has_severe ,
        'count':interactions .count (),
        })


class PrescriptionViewSet (viewsets .ModelViewSet ):
    """Prescriptions management — create, dispense, cancel."""
    queryset =Prescription .objects .select_related ('patient','doctor').prefetch_related ('items__medication').all ()
    permission_classes =[permissions .IsAuthenticated ]
    ordering =['-created_at']

    def get_serializer_class (self ):
        if self .action =='create':
            return PrescriptionCreateSerializer 
        return PrescriptionSerializer 

    def get_queryset (self ):
        qs =super ().get_queryset ()
        status_filter =self .request .query_params .get ('status')
        if status_filter :
            qs =qs .filter (status =status_filter )
        search =self .request .query_params .get ('search','')
        if search :
            qs =qs .filter (
            Q (patient___full_name__icontains =search )|
            Q (doctor__full_name__icontains =search )|
            Q (diagnosis_code__icontains =search )
            )
        return qs 

    @action (detail =True ,methods =['post'])
    def dispense (self ,request ,pk =None ):
        """Dispense a prescription — deducts stock and changes status."""
        prescription =self .get_object ()
        if prescription .status !='ISSUED':
            return Response (
            {'detail':'لا يمكن صرف وصفة بحالة: '+prescription .status },
            status =status .HTTP_400_BAD_REQUEST ,
            )

            # Comment_280
        insufficient =[]
        for item in prescription .items .select_related ('medication').all ():
            if item .medication .stock_quantity <item .quantity :
                insufficient .append ({
                'medication':item .medication .name ,
                'available':item .medication .stock_quantity ,
                'required':item .quantity ,
                })

        if insufficient :
            return Response (
            {'detail':'مخزون غير كافٍ لبعض الأدوية','insufficient':insufficient },
            status =status .HTTP_400_BAD_REQUEST ,
            )

            # Comment_281
        for item in prescription .items .select_related ('medication').all ():
            item .medication .stock_quantity -=item .quantity 
            item .medication .save (update_fields =['stock_quantity'])

        prescription .status ='DISPENSED'
        prescription .save (update_fields =['status'])

        log_security_event (
        user =request .user ,
        event_type ='PRESCRIPTION_DISPENSED',
        request =request ,
        details ={
        'prescription_id':str (prescription .id ),
        'patient':str (prescription .patient_id ),
        'items_count':prescription .items .count (),
        },
        )

        return Response (PrescriptionSerializer (prescription ).data )

    @action (detail =True ,methods =['post'])
    def cancel (self ,request ,pk =None ):
        """Cancel a prescription."""
        prescription =self .get_object ()
        if prescription .status =='DISPENSED':
            return Response (
            {'detail':'لا يمكن إلغاء وصفة تم صرفها'},
            status =status .HTTP_400_BAD_REQUEST ,
            )
        prescription .status ='CANCELLED'
        prescription .save (update_fields =['status'])
        return Response (PrescriptionSerializer (prescription ).data )


class PharmacyStatsView (viewsets .ViewSet ):
    """Pharmacy-wide statistics."""
    permission_classes =[permissions .IsAuthenticated ]

    def list (self ,request ):
        today =timezone .now ().date ()
        cutoff_30 =today +timedelta (days =30 )

        total =Medication .objects .filter (is_active =True ).count ()
        low =Medication .objects .filter (
        is_active =True ,stock_quantity__lte =F ('reorder_level')
        ).count ()
        expired =Medication .objects .filter (
        is_active =True ,expiry_date__lt =today 
        ).count ()
        expiring_soon =Medication .objects .filter (
        is_active =True ,expiry_date__lte =cutoff_30 ,expiry_date__gte =today 
        ).count ()
        stock_value =Medication .objects .filter (is_active =True ).aggregate (
        total =Sum (F ('stock_quantity')*F ('unit_price'))
        )['total']or 0 

        total_rx =Prescription .objects .count ()
        pending_rx =Prescription .objects .filter (status ='ISSUED').count ()
        dispensed_today =Prescription .objects .filter (
        status ='DISPENSED',updated_at__date =today 
        ).count ()

        return Response ({
        'total_medications':total ,
        'low_stock_count':low ,
        'expired_count':expired ,
        'expiring_soon':expiring_soon ,
        'total_stock_value':float (stock_value ),
        'total_prescriptions':total_rx ,
        'pending_prescriptions':pending_rx ,
        'dispensed_today':dispensed_today ,
        })
