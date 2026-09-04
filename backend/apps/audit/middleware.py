"""
Audit logging middleware.
"""
import time 
import logging 
from apps .audit .models import AuditLog 
from apps .audit .utils import log_security_event 

logger =logging .getLogger ('security')


class AuditLogMiddleware :
    """Log API requests to audit log."""

    def __init__ (self ,get_response ):
        self .get_response =get_response 

    def __call__ (self ,request ):
        start_time =time .time ()
        response =self .get_response (request )
        duration =time .time ()-start_time 

        # Comment_120
        if request .path .startswith ('/api/')and hasattr (request ,'user')and request .user .is_authenticated :
            if request .method in ('POST','PUT','PATCH','DELETE'):
            # Comment_121
                if request .method =='POST':
                    event_type ='DATA_CREATED'
                elif request .method in ('PUT','PATCH'):
                    event_type ='DATA_MODIFIED'
                elif request .method =='DELETE':
                    event_type ='DATA_DELETED'
                else :
                    event_type ='SYSTEM_EVENT'

                    # Comment_122
                if 'settings'in request .path or 'config'in request .path :
                    event_type ='CONFIG_CHANGED'

                    # Comment_123
                    # Comment_124
                    # Comment_125
                if not getattr (request ,'_audit_logged',False ):
                    severity =AuditLog .Severity .INFO 
                    if response .status_code >=400 :
                        severity =AuditLog .Severity .WARNING 

                    log_security_event (
                    user =request .user ,
                    event_type =event_type if hasattr (AuditLog .EventType ,event_type )else AuditLog .EventType .SUSPICIOUS_ACTIVITY ,# Comment_126
                    request =request ,
                    details ={
                    'status_code':response .status_code ,
                    'duration_ms':round (duration *1000 ,2 )
                    },
                    severity =severity 
                    )

        return response 
