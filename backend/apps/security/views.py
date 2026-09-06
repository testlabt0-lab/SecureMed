"""
Views for security tools: Port Scanner + Vulnerability Scanner.
"""
import logging
from rest_framework import status ,permissions
from rest_framework .decorators import action
from rest_framework .response import Response
from rest_framework .views import APIView
from rest_framework .viewsets import ViewSet

from django .conf import settings

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
        # Run vulnerability scan (quick)
            vuln_report =run_vulnerability_scan ()

            # Quick port scan of localhost
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
            'security_features':self ._security_features (request ),
            })
        except Exception as e :
            logger .error (f"Security dashboard failed: {e }")
            return Response (
            {'detail':f'فشل لوحة الأمان: {str (e )}'},
            status =status .HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _security_features (self ,request ):
        """Report the controls that are actually configured.

        This block used to be a literal: secure=True, waf_active=True,
        tls_enabled=True, jwt_algorithm='RS256' — regardless of what the deployment
        was really running. On a stack signing with HS256 and serving over plain HTTP
        it still displayed a clean sheet, which is worse than showing nothing: an
        auditor reads it and concludes the controls are on. Every value below is now
        derived from settings or from the request in front of us.
        """
        middleware =[str (m )for m in getattr (settings ,'MIDDLEWARE',[])]
        jwt_conf =getattr (settings ,'SIMPLE_JWT',{})or {}
        cache_backend =(getattr (settings ,'CACHES',{}).get ('default',{}).get ('BACKEND','')or '')
        channel_backend =(getattr (settings ,'CHANNEL_LAYERS',{}).get ('default',{}).get ('BACKEND','')or '')

        return {
        # The refresh cookie is written by apps.accounts.views.set_refresh_cookie,
        # which flips `secure` off under DEBUG so local HTTP development works.
        'refresh_cookie_flags':{
        'secure':not settings .DEBUG ,
        'httponly':True ,
        'samesite':'Strict',
        },
        'session_cookie_flags':{
        'secure':bool (getattr (settings ,'SESSION_COOKIE_SECURE',False )),
        'httponly':bool (getattr (settings ,'SESSION_COOKIE_HTTPONLY',False )),
        'samesite':getattr (settings ,'SESSION_COOKIE_SAMESITE',None ),
        'age_seconds':getattr (settings ,'SESSION_COOKIE_AGE',None ),
        },
        'csrf_cookie_secure':bool (getattr (settings ,'CSRF_COOKIE_SECURE',False )),
        'waf_active':any ('WAFMiddleware'in m for m in middleware ),
        'rate_limit_active':any ('RateLimitMiddleware'in m for m in middleware ),
        'session_binding_active':any ('SessionSecurityMiddleware'in m for m in middleware ),
        'audit_middleware_active':any ('AuditLogMiddleware'in m for m in middleware ),
        # Field-level encryption of specific PHI columns — not full-disk encryption.
        'field_encryption_enabled':bool (getattr (settings ,'USE_FIELD_ENCRYPTION',False )),
        'https_redirect':bool (getattr (settings ,'SECURE_SSL_REDIRECT',False )),
        'hsts_seconds':getattr (settings ,'SECURE_HSTS_SECONDS',0 ),
        'request_is_secure':request .is_secure (),
        'jwt_algorithm':jwt_conf .get ('ALGORITHM','HS256'),
        'jwt_rotate_refresh':bool (jwt_conf .get ('ROTATE_REFRESH_TOKENS',False )),
        'jwt_blacklist_after_rotation':bool (jwt_conf .get ('BLACKLIST_AFTER_ROTATION',False )),
        'jwt_access_lifetime_seconds':(
        int (jwt_conf ['ACCESS_TOKEN_LIFETIME'].total_seconds ())
        if jwt_conf .get ('ACCESS_TOKEN_LIFETIME')else None
        ),
        # A per-process cache makes rate limiting, the JWT denylist and the WAF
        # blocklists unenforceable across workers, so it belongs on this panel.
        'shared_cache':'locmem'not in cache_backend .lower (),
        'shared_channel_layer':'InMemoryChannelLayer'not in channel_backend ,
        # A dedicated audit key means SECRET_KEY rotation cannot silently
        # invalidate the audit chain. Only whether one is set is reported.
        'audit_chain_dedicated_key':bool (getattr (settings ,'AUDIT_LOG_HMAC_KEY','')),
        'media_access_controlled':bool (getattr (settings ,'PROTECT_MEDIA_FILES',True ))and not settings .DEBUG ,
        # Uploaded files (imaging, lab reports, scanned documents) encrypted on disk
        # with AES-256-GCM — see apps.core.storage. Reported separately from
        # field_encryption_enabled because until now the columns were encrypted and
        # the files next to them were not.
        'media_encrypted_at_rest':(
        bool (getattr (settings ,'ENCRYPT_MEDIA_AT_REST',False ))
        or bool (getattr (settings ,'USE_S3_STORAGE',False ))and bool (getattr (settings ,'AWS_S3_ENCRYPTION',False ))
        ),
        # Whether a retired ENCRYPTION_KEY is still accepted for reads. True is not a
        # finding in itself — it is the normal state mid-rotation — but it should not
        # stay true indefinitely: run `manage.py rotate_encryption_key`, then drop the
        # old key. Only the count is reported, never a key.
        'encryption_key_fallbacks':len (getattr (settings ,'ENCRYPTION_KEY_FALLBACKS',[])),
        'api_docs_exposed':bool (getattr (settings ,'ENABLE_API_DOCS',settings .DEBUG )),
        'debug_mode':settings .DEBUG ,
        }

