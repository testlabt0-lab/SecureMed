"""
Dashboard analytics models for tracking system metrics.
"""
import uuid 
from django .db import models 
from django .utils .translation import gettext_lazy as _ 
from django .conf import settings 
from django .utils import timezone 
from datetime import timedelta 


class SystemMetric (models .Model ):
    """
    System-wide metrics for dashboard analytics.
    Tracks aggregated statistics over time.
    """

    class MetricType (models .TextChoices ):
        ACTIVE_USERS ='ACTIVE_USERS',_ ('المستخدمون النشطون')
        ACTIVE_CHANNELS ='ACTIVE_CHANNELS',_ ('القنوات النشطة')
        TOTAL_PATIENTS ='TOTAL_PATIENT',_ ('إجمالي المرضى')
        MEDICAL_RECORDS ='MEDICAL_RECORDS',_ ('السجلات الطبية')
        SECURITY_ALERTS ='SECURITY_ALERTS',_ ('تنبيهات الأمان')
        WAF_BLOCKS ='WAF_BLOCKS',_ ('حظر WAF')
        FAILED_LOGINS ='FAILED_LOGINS',_ ('تسجيلات الدخول الفاشلة')
        BIOMETRIC_LOGINS ='BIOMETRIC_LOGINS',_ ('دخول بيوميتري')
        API_REQUESTS ='API_REQUESTS',_ ('طلبات API')
        FILE_UPLOADS ='FILE_UPLOADS',_ ('رفع الملفات')

    id =models .UUIDField (primary_key =True ,default =uuid .uuid4 ,editable =False )
    metric_type =models .CharField (
    _ ('نوع المقياس'),max_length =30 ,
    choices =MetricType .choices ,db_index =True 
    )
    value =models .BigIntegerField (_ ('القيمة'),default =0 )
    date =models .DateField (_ ('التاريخ'),db_index =True )
    hour =models .PositiveSmallIntegerField (null =True ,blank =True )# Comment_67
    metadata =models .JSONField (default =dict ,blank =True )

    created_at =models .DateTimeField (auto_now_add =True )

    class Meta :
        verbose_name =_ ('مقياس النظام')
        verbose_name_plural =_ ('مقاييس النظام')
        ordering =['-date','-hour']
        unique_together =['metric_type','date','hour']
        indexes =[
        models .Index (fields =['metric_type','-date']),
        models .Index (fields =['date','hour']),
        ]


class UserActivity (models .Model ):
    """
    Track user activity for analytics and audit.
    Aggregated to SystemMetric periodically.
    """
    id =models .UUIDField (primary_key =True ,default =uuid .uuid4 ,editable =False )
    user =models .ForeignKey (
    settings .AUTH_USER_MODEL ,
    on_delete =models .SET_NULL ,null =True ,
    related_name ='activities',
    )
    activity_type =models .CharField (max_length =50 ,db_index =True )
    description =models .TextField (blank =True )
    ip_address =models .GenericIPAddressField (null =True ,blank =True )
    metadata =models .JSONField (default =dict ,blank =True )
    timestamp =models .DateTimeField (auto_now_add =True ,db_index =True )

    class Meta :
        verbose_name =_ ('نشاط المستخدم')
        verbose_name_plural =_ ('أنشطة المستخدمين')
        ordering =['-timestamp']
        indexes =[
        models .Index (fields =['user','-timestamp']),
        models .Index (fields =['activity_type','-timestamp']),
        ]


class SecurityDashboardStat (models .Model ):
    """
    Cached security dashboard statistics.
    Updated periodically to avoid expensive queries.
    """
    id =models .UUIDField (primary_key =True ,default =uuid .uuid4 ,editable =False )
    stat_key =models .CharField (max_length =100 ,unique =True ,db_index =True )
    stat_value =models .JSONField (default =dict )
    last_updated =models .DateTimeField (auto_now =True )

    class Meta :
        verbose_name =_ ('إحصائية الأمان')
        verbose_name_plural =_ ('إحصائيات الأمان')

    @classmethod 
    def get_stat (cls ,key ,default =None ):
        """Get a cached stat value."""
        try :
            return cls .objects .get (stat_key =key ).stat_value 
        except cls .DoesNotExist :
            return default 

    @classmethod 
    def set_stat (cls ,key ,value ):
        """Set a cached stat value."""
        obj ,created =cls .objects .update_or_create (
        stat_key =key ,
        defaults ={'stat_value':value }
        )
        return obj 
