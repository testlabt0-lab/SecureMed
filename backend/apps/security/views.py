"""
Views for security tools: Port Scanner + Vulnerability Scanner.
"""
import logging 
from rest_framework import status ,permissions 
from rest_framework .decorators import action 
from rest_framework .response import Response 
from rest_framework .views import APIView 
from rest_framework .viewsets import ViewSet 

from apps .security .permissions import IsAdmin ,IsAuditor 
from apps .security .port_scanner import scan_host_ports 
from apps .security .vulnerability_scanner import run_vulnerability_scan 
from apps .audit .utils import log_security_event 

logger =logging .getLogger ('security')


class PortScannerView (APIView ):
    """
    Security requirement #2: أداة مسح المنافذ (Port Scanner)
    Scans target host for open ports (limited to private IPs for safety).
    """
    permission_classes =[IsAdmin |IsAuditor ]

    def post (self ,request ):
        target =request .data .get ('target','localhost')
        ports =request .data .get ('ports')

        if ports and not isinstance (ports ,list ):
            return Response (
            {'detail':'ports يجب أن تكون قائمة أرقام'},
            status =status .HTTP_400_BAD_REQUEST 
            )

        try :
            result =scan_host_ports (target ,ports )
            log_security_event (
            user =request .user ,
            event_type ='PORT_SCAN_EXECUTED',
            request =request ,
            details ={'target':target ,'open_ports':result ['open_ports']}
            )
            return Response (result )
        except ValueError as e :
            return Response (
            {'detail':str (e )},
            status =status .HTTP_400_BAD_REQUEST 
            )
        except Exception as e :
            logger .error (f"Port scan failed: {e }")
            return Response (
            {'detail':f'فشل المسح: {str (e )}'},
            status =status .HTTP_500_INTERNAL_SERVER_ERROR 
            )


class VulnerabilityScannerView (APIView ):
    """
    Security requirement #4: أداة فحص الثغرات الأمنية (Vulnerability Scanner)
    Scans the application for OWASP Top 10 vulnerabilities.
    """
    permission_classes =[IsAdmin |IsAuditor ]

    def post (self ,request ):
        try :
            result =run_vulnerability_scan ()
            log_security_event (
            user =request .user ,
            event_type ='VULN_SCAN_EXECUTED',
            request =request ,
            details ={
            'risk_score':result ['risk_score'],
            'total_vulns':result ['summary']['total']
            }
            )
            return Response (result )
        except Exception as e :
            logger .error (f"Vulnerability scan failed: {e }")
            return Response (
            {'detail':f'فشل الفحص: {str (e )}'},
            status =status .HTTP_500_INTERNAL_SERVER_ERROR 
            )


class SecurityDashboardView (APIView ):
    """
    Combined security dashboard: runs both scanners and returns a summary.
    """
    permission_classes =[IsAdmin |IsAuditor ]

    def get (self ,request ):
        try :
        # Comment_387
            vuln_report =run_vulnerability_scan ()

            # Comment_388
            port_report =scan_host_ports ('localhost')

            return Response ({
            'vulnerability_scan':{
            'risk_score':vuln_report ['risk_score'],
            'summary':vuln_report ['summary'],
            'top_vulnerabilities':vuln_report ['vulnerabilities'][:5 ],
            },
            'port_scan':{
            'target':port_report ['target'],
            'open_ports':port_report ['open_ports'],
            'high_risk_ports':[
            p for p in port_report ['results']
            if p ['state']=='open'and p ['risk_level']=='critical'
            ],
            'risk_assessment':port_report ['risk_assessment'],
            },
            'security_features':{
            'cookie_flags':{
            'secure':True ,# Comment_389
            'httponly':True ,
            'samesite':'Strict',
            },
            'waf_active':True ,
            'encryption_at_rest':True ,
            'tls_enabled':True ,
            'jwt_algorithm':'RS256',
            },
            })
        except Exception as e :
            logger .error (f"Security dashboard failed: {e }")
            return Response (
            {'detail':f'فشل لوحة الأمان: {str (e )}'},
            status =status .HTTP_500_INTERNAL_SERVER_ERROR 
            )
