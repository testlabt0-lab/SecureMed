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
from apps .core .mixins import accessible_patients 
from apps .patients .models import Patient 

from .models import (
Medication ,DrugInteraction ,Prescription ,PrescriptionItem ,
MedicationPlan ,
)
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
        # Filter options
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
        else :# ADJUSTMENT
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

    def perform_create (self ,serializer ):
        """Create a prescription — the doctor is the caller.

        The serializer already sets `doctor = request.user`; the audit event
        was the missing half: creation was the only prescription lifecycle
        step (dispense, cancel) with no trail.
        """
        prescription =serializer .save ()
        log_security_event (
        user =self .request .user ,
        event_type ='PRESCRIPTION_CREATED',
        request =self .request ,
        details ={
        'prescription_id':str (prescription .id ),
        'patient':str (prescription .patient_id ),
        'items_count':prescription .items .count (),
        },
        )

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

            # Verify stock availability for all items
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

            # Deduct stock
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


class MedicationPlanSyncView (viewsets .ViewSet ):
    """Server twin of the Android app's device-local medication plans.

    GET  /api/v1/pharmacy/medication-plans/?patient=<id>
         Plans the caller may see for one patient (or all their accessible
         patients when patient is omitted) — the pull half of the sync.

    POST /api/v1/pharmacy/medication-plans/
         Upsert one plan by `source_id`: the Android client's local plan UUID.
         Re-pushing the same plan updates instead of duplicating.

    The Android client keeps plans locally so alarms fire offline; these rows
    are the durable copy that survives a reinstall and lets the care team
    adjust a regimen centrally. Plan names are encrypted at rest.
    """
    permission_classes =[permissions .IsAuthenticated ]

    def _scoped_patients (self ,request ):
        return accessible_patients (Patient .objects .all (),request .user )

    def list (self ,request ):
        patient_param =request .query_params .get ('patient')
        qs =MedicationPlan .objects .select_related ('patient','created_by')
        if patient_param :
            try :
                patient_qs =self ._scoped_patients (request ).filter (pk =patient_param )
            except Exception :
                return Response ({'detail':'معرف مريض غير صالح'},status =400 )
            if not patient_qs .exists ():
                # Same 404-not-403 contract as the FHIR endpoints.
                return Response ({'detail':'غير موجود'},status =404 )
            qs =qs .filter (patient_id =patient_param )
        else :
            patient_ids =list (
            self ._scoped_patients (request ).values_list ('id',flat =True )[:500 ]
            )
            qs =qs .filter (patient_id__in =patient_ids )

        active =request .query_params .get ('active')
        if active is not None :
            qs =qs .filter (is_active =(active .lower ()=='true'))

        qs =qs .order_by ('-created_at')[:200 ]
        return Response ([self ._serialize (p )for p in qs ])

    def create (self ,request ):
        data =request .data 
        patient_id =data .get ('patient_id')
        if not patient_id :
            return Response ({'detail':'patient_id مطلوب'},status =400 )
        try :
            patient =self ._scoped_patients (request ).get (pk =patient_id )
        except Patient .DoesNotExist :
            return Response ({'detail':'غير مصرح أو غير موجود'},status =404 )

        name =str (data .get ('name')or '').strip ()
        dosage =str (data .get ('dosage')or '').strip ()
        times =data .get ('times')or []
        if not name or not dosage or not data .get ('start_date'):
            return Response (
            {'detail':'الاسم والجرعة وتاريخ البدء مطلوبة'},status =400 
            )
        if not isinstance (times ,list )or len (times )>12 :
            return Response ({'detail':'قائمة الأوقات غير صالحة'},status =400 )
        times =sorted ({str (t )[:5 ]for t in times })

        # Coerce before save: a DateField holds the raw string until it is
        # written to the database, so serialising a freshly-created object in
        # the same request would otherwise call .isoformat() on a str.
        import datetime as _dt 
        try :
            start_date =_dt .date .fromisoformat (str (data ['start_date']))
        except (TypeError ,ValueError ):
            return Response ({'detail':'صيغة تاريخ البدء غير صالحة (YYYY-MM-DD)'},status =400 )
        end_date =data .get ('end_date')or None 
        if end_date :
            try :
                end_date =_dt .date .fromisoformat (str (end_date ))
            except (TypeError ,ValueError ):
                return Response ({'detail':'صيغة تاريخ الانتهاء غير صالحة (YYYY-MM-DD)'},status =400 )

        source_id =data .get ('source_id')or None 
        plan =None 
        is_update =False 
        if source_id :
            plan =MedicationPlan .objects .filter (
            patient =patient ,source_id =source_id 
            ).first ()
            is_update =plan is not None 

        if plan is None :
            plan =MedicationPlan (
            patient =patient ,
            created_by =request .user ,
            source_id =source_id ,
            name =name ,
            )
        plan .dosage =dosage 
        plan .times =times 
        plan .start_date =start_date 
        plan .end_date =end_date 
        plan .instructions =str (data .get ('instructions')or '')[:2000 ]
        plan .is_active =bool (data .get ('is_active',True ))
        plan .save ()

        log_security_event (
        user =request .user ,
        event_type ='DATA_MODIFIED'if is_update else 'DATA_CREATED',
        request =request ,
        details ={'plan_id':str (plan .id ),'patient_id':str (patient .id ),
        'via':'medication_plan_sync'},
        )
        return Response (self ._serialize (plan ),status =200 if is_update else 201 )

    @staticmethod 
    def _serialize (plan ):
        return {
        'id':str (plan .id ),
        'source_id':str (plan .source_id )if plan .source_id else None ,
        'patient_id':str (plan .patient_id ),
        'patient_name':plan .patient .full_name ,
        'name':plan .name ,
        'dosage':plan .dosage ,
        'times':plan .times ,
        'start_date':plan .start_date .isoformat ()if plan .start_date else None ,
        'end_date':plan .end_date .isoformat ()if plan .end_date else None ,
        'instructions':plan .instructions ,
        'is_active':plan .is_active ,
        'prescribed_by':plan .created_by .full_name ,
        'created_at':plan .created_at .isoformat ()if plan .created_at else None ,
        'updated_at':plan .updated_at .isoformat ()if plan .updated_at else None ,
        }


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
