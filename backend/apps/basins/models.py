"""
Basin (الحوض الصحي) models.

Implements the plan requirement:
  «يجب أن ترتبط بالأحواز وتُفعّل بحسب نوع الأحواز»
  — every clinical object (user / patient / channel) is linked to a basin,
    and the system modules available inside that basin are activated
    according to the basin TYPE (hospital vs health-center vs unit...).
"""
import uuid 

from django .db import models 
from django .core .exceptions import ValidationError 
from django .utils .translation import gettext_lazy as _ 

from apps .audit .utils import log_security_event 


class Basin (models .Model ):
    """
    حوض صحي — a health facility / catchment organisational unit.

    The basin type controls which system modules are ACTIVE for everyone
    working inside it (module activation by basin type). An administrator
    can still fine-tune individual modules after creation.
    """

    class BasinType (models .TextChoices ):
        GENERAL_HOSPITAL ='GENERAL_HOSPITAL',_ ('مستشفى عام')
        SPECIALIZED_HOSPITAL ='SPECIALIZED_HOSPITAL',_ ('مستشفى تخصصي')
        RURAL_HOSPITAL ='RURAL_HOSPITAL',_ ('مستشفى ريفي')
        HEALTH_CENTER ='HEALTH_CENTER',_ ('مركز صحي')
        HEALTH_UNIT ='HEALTH_UNIT',_ ('وحدة صحية')
        DIALYSIS_CENTER ='DIALYSIS_CENTER',_ ('مركز غسيل كلوي')
        SPECIALIZED_CLINIC ='SPECIALIZED_CLINIC',_ ('مركز/عيادة تخصصية')

        # Comment_155
        # Comment_156
        # Comment_157
    MODULE_PATIENTS ='patients'
    MODULE_CHANNELS ='channels'
    MODULE_MEDICAL_FILES ='medical_files'
    MODULE_LAB ='lab'
    MODULE_PHARMACY ='pharmacy'
    MODULE_AI_ASSISTANT ='ai_assistant'
    MODULE_REPORTS ='reports'
    MODULE_ANALYTICS ='analytics'

    ALL_MODULES =[
    MODULE_PATIENTS ,
    MODULE_CHANNELS ,
    MODULE_MEDICAL_FILES ,
    MODULE_LAB ,
    MODULE_PHARMACY ,
    MODULE_AI_ASSISTANT ,
    MODULE_REPORTS ,
    MODULE_ANALYTICS ,
    ]

    MODULE_LABELS ={
    MODULE_PATIENTS :_ ('سجلات المرضى'),
    MODULE_CHANNELS :_ ('قنوات الحالات'),
    MODULE_MEDICAL_FILES :_ ('الملفات الطبية'),
    MODULE_LAB :_ ('المختبر'),
    MODULE_PHARMACY :_ ('الصيدلية'),
    MODULE_AI_ASSISTANT :_ ('المساعد الذكي'),
    MODULE_REPORTS :_ ('التقارير'),
    MODULE_ANALYTICS :_ ('التحليلات'),
    }

    # Comment_158
    # Comment_159
    # Comment_160
    # Comment_161
    DEFAULT_MODULES_BY_TYPE ={
    BasinType .GENERAL_HOSPITAL :ALL_MODULES ,
    BasinType .SPECIALIZED_HOSPITAL :[
    MODULE_PATIENTS ,MODULE_CHANNELS ,MODULE_MEDICAL_FILES ,
    MODULE_LAB ,MODULE_PHARMACY ,MODULE_AI_ASSISTANT ,
    MODULE_REPORTS ,MODULE_ANALYTICS ,
    ],
    BasinType .RURAL_HOSPITAL :[
    MODULE_PATIENTS ,MODULE_CHANNELS ,MODULE_MEDICAL_FILES ,
    MODULE_LAB ,MODULE_REPORTS ,
    ],
    BasinType .HEALTH_CENTER :[
    MODULE_PATIENTS ,MODULE_CHANNELS ,MODULE_MEDICAL_FILES ,
    MODULE_REPORTS ,
    ],
    BasinType .HEALTH_UNIT :[
    MODULE_PATIENTS ,MODULE_CHANNELS ,
    ],
    BasinType .DIALYSIS_CENTER :[
    MODULE_PATIENTS ,MODULE_CHANNELS ,MODULE_MEDICAL_FILES ,
    MODULE_REPORTS ,
    ],
    BasinType .SPECIALIZED_CLINIC :[
    MODULE_PATIENTS ,MODULE_CHANNELS ,MODULE_MEDICAL_FILES ,
    ],
    }

    id =models .UUIDField (primary_key =True ,default =uuid .uuid4 ,editable =False )
    name =models .CharField (_ ('اسم الحوض'),max_length =200 ,unique =True )
    code =models .CharField (
    _ ('الرمز'),max_length =30 ,unique =True ,
    help_text =_ ('رمز قصير فريد مثل: THH-SAN-01')
    )
    basin_type =models .CharField (
    _ ('نوع الحوض'),max_length =30 ,choices =BasinType .choices ,
    default =BasinType .HEALTH_CENTER ,
    help_text =_ ('نوع الحوض يحدد الوحدات المفعّلة تلقائياً'),
    )
    governorate =models .CharField (_ ('المحافظة'),max_length =100 ,blank =True )
    directorate =models .CharField (_ ('المديرية'),max_length =100 ,blank =True )
    address =models .CharField (_ ('العنوان'),max_length =255 ,blank =True )
    phone =models .CharField (_ ('الهاتف'),max_length =30 ,blank =True )
    email =models .EmailField (_ ('البريد الإلكتروني'),blank =True )
    manager =models .ForeignKey (
    'accounts.User',on_delete =models .SET_NULL ,null =True ,blank =True ,
    related_name ='managed_basins',verbose_name =_ ('مدير الحوض'),
    )
    bed_capacity =models .PositiveIntegerField (_ ('الطاقة الاستيعابية (أسرّة)'),null =True ,blank =True )

    # Comment_162
    # Comment_163
    enabled_modules =models .JSONField (
    _ ('الوحدات المفعّلة'),default =list ,blank =True ,
    help_text =_ ('قائمة الوحدات المفعّلة في هذا الحوض'),
    )

    is_active =models .BooleanField (_ ('نشط'),default =True )
    notes =models .TextField (_ ('ملاحظات'),blank =True )
    created_at =models .DateTimeField (auto_now_add =True )
    updated_at =models .DateTimeField (auto_now =True )

    class Meta :
        verbose_name =_ ('حوض صحي')
        verbose_name_plural =_ ('الأحواز الصحية')
        ordering =['name']
        indexes =[
        models .Index (fields =['basin_type','is_active']),
        ]

    def __str__ (self ):
        return f'{self .name } ({self .get_basin_type_display ()})'

        # Comment_164
        # Comment_165
        # Comment_166
    def apply_default_modules (self ,save =True ):
        """Activate modules according to the basin TYPE (plan requirement)."""
        self .enabled_modules =list (
        self .DEFAULT_MODULES_BY_TYPE .get (self .basin_type ,[])
        )
        if save :
            self .save (update_fields =['enabled_modules','updated_at'])
        return self .enabled_modules 

    def has_module (self ,module :str )->bool :
        """Is a system module activated inside this basin?"""
        return module in (self .enabled_modules or [])

    def enable_module (self ,module :str ):
        if module not in self .ALL_MODULES :
            raise ValidationError (_ ('وحدة غير معروفة: %s')%module )
        if module not in self .enabled_modules :
            self .enabled_modules .append (module )
            self .save (update_fields =['enabled_modules','updated_at'])

    def disable_module (self ,module :str ):
        if module in self .enabled_modules :
            self .enabled_modules .remove (module )
            self .save (update_fields =['enabled_modules','updated_at'])

    def save (self ,*args ,**kwargs ):
    # Comment_167
        if not self .enabled_modules :
            self .enabled_modules =list (
            self .DEFAULT_MODULES_BY_TYPE .get (self .basin_type ,[])
            )
        super ().save (*args ,**kwargs )

        # Comment_168
        # Comment_169
        # Comment_170
    def stats (self )->dict :
        from apps .accounts .models import User 
        from apps .patients .models import Patient 
        from apps .channels .models import Channel 

        return {
        'users':User .objects .filter (basin =self ).count (),
        'patients':Patient .objects .filter (basin =self ).count (),
        'channels':Channel .objects .filter (basin =self ).count (),
        'active_channels':Channel .objects .filter (
        basin =self ,status =Channel .Status .ACTIVE 
        ).count (),
        }
