import uuid 
from django .db import models 
from django .conf import settings 
from django .utils .translation import gettext_lazy as _ 

class Medication (models .Model ):
    """Pharmacy inventory and drug catalog."""
    id =models .UUIDField (primary_key =True ,default =uuid .uuid4 ,editable =False )
    name =models .CharField (_ ('اسم الدواء'),max_length =255 ,db_index =True )
    scientific_name =models .CharField (_ ('الاسم العلمي'),max_length =255 ,blank =True )
    barcode =models .CharField (_ ('الباركود'),max_length =100 ,unique =True ,null =True ,blank =True )

    # Comment_273
    stock_quantity =models .PositiveIntegerField (_ ('الكمية المتوفرة'),default =0 )
    reorder_level =models .PositiveIntegerField (_ ('حد إعادة الطلب'),default =10 )
    unit_price =models .DecimalField (_ ('سعر الوحدة'),max_digits =10 ,decimal_places =2 ,default =0.00 )
    expiry_date =models .DateField (_ ('تاريخ الانتهاء'),null =True ,blank =True )

    # Comment_274
    description =models .TextField (_ ('الوصف'),blank =True )
    instructions =models .TextField (_ ('تعليمات عامة'),blank =True )
    is_active =models .BooleanField (_ ('نشط'),default =True )

    class Meta :
        verbose_name =_ ('دواء')
        verbose_name_plural =_ ('الأدوية')
        ordering =['name']

    def __str__ (self ):
        return f"{self .name } ({self .stock_quantity })"

class DrugInteraction (models .Model ):
    """Rules to warn doctors when prescribing conflicting drugs."""
    id =models .UUIDField (primary_key =True ,default =uuid .uuid4 ,editable =False )
    drug_a =models .ForeignKey (Medication ,on_delete =models .CASCADE ,related_name ='interactions_as_a')
    drug_b =models .ForeignKey (Medication ,on_delete =models .CASCADE ,related_name ='interactions_as_b')
    severity =models .CharField (_ ('الخطورة'),max_length =50 ,choices =[
    ('MILD',_ ('خفيف')),
    ('MODERATE',_ ('متوسط')),
    ('SEVERE',_ ('خطير')),
    ],default ='MODERATE')
    description =models .TextField (_ ('وصف التداخل'))

    class Meta :
        verbose_name =_ ('تداخل دوائي')
        verbose_name_plural =_ ('التداخلات الدوائية')
        unique_together =['drug_a','drug_b']

class Prescription (models .Model ):
    """Electronic prescription securely signed by the doctor."""
    id =models .UUIDField (primary_key =True ,default =uuid .uuid4 ,editable =False )
    patient =models .ForeignKey ('patients.Patient',on_delete =models .CASCADE ,related_name ='prescriptions')
    doctor =models .ForeignKey (settings .AUTH_USER_MODEL ,on_delete =models .CASCADE ,related_name ='prescriptions_issued')

    # Comment_275
    diagnosis_code =models .CharField (_ ('رمز التشخيص ICD-10'),max_length =50 ,blank =True )

    # Comment_276
    digital_signature =models .TextField (_ ('التوقيع الرقمي'),blank =True ,help_text =_ ('توقيع مشفر يثبت صحة الوصفة'))
    is_signed =models .BooleanField (_ ('موقعة إلكترونياً'),default =False )
    signed_at =models .DateTimeField (_ ('تاريخ التوقيع'),null =True ,blank =True )

    notes =models .TextField (_ ('ملاحظات الصيدلي'),blank =True )
    status =models .CharField (_ ('الحالة'),max_length =50 ,choices =[
    ('ISSUED',_ ('مصدرة')),
    ('DISPENSED',_ ('مصروفة')),
    ('CANCELLED',_ ('ملغاة')),
    ],default ='ISSUED')

    created_at =models .DateTimeField (auto_now_add =True )
    updated_at =models .DateTimeField (auto_now =True )

    class Meta :
        verbose_name =_ ('وصفة طبية')
        verbose_name_plural =_ ('الوصفات الطبية')
        ordering =['-created_at']

    def sign (self ,private_key_pem :str ,password :str =None ):
        """Signs the prescription using doctor's private key."""
        from apps .security .utils .digital_signature import DigitalSignatureService 
        from django .utils import timezone 

        # Comment_277
        data_to_sign ={
        'prescription_id':str (self .id ),
        'patient_id':str (self .patient .id ),
        'doctor_id':str (self .doctor .id ),
        'diagnosis_code':self .diagnosis_code ,
        'created_at':self .created_at .isoformat ()if self .created_at else timezone .now ().isoformat (),
        }

        signature =DigitalSignatureService .sign_prescription (data_to_sign ,private_key_pem ,password )
        self .digital_signature =signature 
        self .is_signed =True 
        self .signed_at =timezone .now ()
        self .save (update_fields =['digital_signature','is_signed','signed_at'])

    def get_qr_code_base64 (self ):
        """Generates a base64 encoded QR Code containing the prescription ID and digital signature."""
        if not self .is_signed or not self .digital_signature :
            return None 

        import qrcode 
        import io 
        import base64 
        import json 

        qr_data =json .dumps ({
        "prescription_id":str (self .id ),
        "signature":self .digital_signature 
        })

        qr =qrcode .QRCode (
        version =1 ,
        error_correction =qrcode .constants .ERROR_CORRECT_L ,
        box_size =10 ,
        border =4 ,
        )
        qr .add_data (qr_data )
        qr .make (fit =True )

        img =qr .make_image (fill_color ="black",back_color ="white")
        buffer =io .BytesIO ()
        img .save (buffer ,format ="PNG")

        return base64 .b64encode (buffer .getvalue ()).decode ('utf-8')

class PrescriptionItem (models .Model ):
    """Individual drug in a prescription."""
    id =models .UUIDField (primary_key =True ,default =uuid .uuid4 ,editable =False )
    prescription =models .ForeignKey (Prescription ,on_delete =models .CASCADE ,related_name ='items')
    medication =models .ForeignKey (Medication ,on_delete =models .PROTECT )

    dosage =models .CharField (_ ('الجرعة'),max_length =255 )
    frequency =models .CharField (_ ('التكرار'),max_length =255 )
    duration_days =models .PositiveIntegerField (_ ('المدة (أيام)'),default =1 )
    quantity =models .PositiveIntegerField (_ ('الكمية المطلوبة'),default =1 )

    def __str__ (self ):
        return f"{self .medication .name } - {self .dosage }"
