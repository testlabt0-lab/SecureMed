"""
WAF (Web Application Firewall) middleware.

Security requirement #5: حماية قاعدة البيانات بأداة عازلة (DB Firewall)
Detects and blocks malicious requests: SQL injection, XSS, path traversal, etc.
"""
import re
import logging
from django .http import JsonResponse
from django .utils import timezone
from django .core .cache import cache

logger =logging .getLogger ('security')

# Patterns that indicate an attack
ATTACK_PATTERNS ={
'SQL_INJECTION':[
# Quote followed by an SQL keyword (whitespace-tolerant).
# NOTE: this pattern intentionally does NOT match a bare quote
# followed by whitespace — quoted values that merely *start with a
# space* (common in JSON bodies) must not be flagged.
r"('|\")\s*(?:--|#|/\*|\*/|;|union\s+select|union\s+all|select\s+.*\s+from|insert\s+into|update\s+\w+\s+set|drop\s+table|drop\s+database|alter\s+table|create\s+table|exec\s*\()",
r"(union\s+select|select\s+.*\s+from|insert\s+into|update\s+\w+\s+set)",
r"(\bor\s+1\s*=\s*1\b|\band\s+1\s*=\s*1\b|\bor\s+'\d+'\s*=\s*'?\d+'?|\band\s+'[^']*'\s*=\s*')",
r"(\bexec\b\s*\(|\bexecute\b\s*\(|\bsp_\w+)",
r"(\bxp_cmdshell\b|\bsp_executesql\b)",
r"(--\s*$|/\*.*\*/)",
r"(\bwaitfor\s+delay\b|\bbenchmark\s*\()",
r"(\bconvert\s*\(|\bcast\s*\(|\bchar\s*\()",
],
'XSS':[
r"(<script|</script|javascript:|onerror=|onload=|onmouse)",
r"(<iframe|<embed|<object|<applet|<form)",
r"(document\.cookie|document\.location|window\.location)",
r"(\balert\s*\(|\bconfirm\s*\(|\bprompt\s*\()",
r"(\beval\s*\(|\bexpression\s*\()",
r"(<img[^>]+src\s*=|<body[^>]+onload)",
],
'PATH_TRAVERSAL':[
r"(\.\./|\.\.\\|/etc/passwd|/etc/shadow|/etc/hosts)",
r"(c:\\windows\\system32|c:\\winnt)",
r"(file://|php://|expect://)",
],
'COMMAND_INJECTION':[
r"(;\s*(ls|cat|pwd|id|whoami|uname|ifconfig|ping|wget|curl))",
r"(\|\s*(ls|cat|pwd|id|whoami))",
r"(`[^`]+`|\$\([^)]+\))",
r"(&&\s*(ls|cat|pwd|id|whoami))",
],
'XXE':[
r"(<!ENTITY|<!DOCTYPE[^>]*\[)",
r"(<\?xml.*\?>.*<!ENTITY)",
r"(SYSTEM\s+[\"']file://)",
],
'SSRF':[
r"(http://localhost|https://localhost)",
r"(http://127\.0\.0\.1|https://127\.0\.0\.1)",
r"(http://169\.254\.169\.254|http://metadata)",
r"(http://0\.0\.0\.0|https://0\.0\.0\.0)",
],
}

# Bodies larger than this are not scanned. Reading ``request.body`` buffers the
# whole payload in memory, which is the wrong thing to do to a file upload.
MAX_BODY_SCAN_BYTES =100000


class WAFMiddleware :
    """
    Web Application Firewall middleware.

    Detects and blocks:
    - SQL Injection attempts
    - Cross-Site Scripting (XSS)
    - Path Traversal
    - Command Injection
    - XXE attacks
    - SSRF attempts
    """

    def __init__ (self ,get_response ):
        self .get_response =get_response 
        self .compiled_patterns ={
        attack_type :[re .compile (p ,re .IGNORECASE )for p in patterns ]
        for attack_type ,patterns in ATTACK_PATTERNS .items ()
        }

    def __call__ (self ,request ):
    # Skip WAF for admin and health check
        if request .path .startswith ('/admin/')or request .path =='/health/':
            return self .get_response (request )

        client_ip =self ._get_client_ip (request )
        device_fingerprint =request .META .get ('HTTP_X_DEVICE_FINGERPRINT','')

        # 1. Check IP Blacklist (cache first, then DB)
        blacklist_key =f'waf_blacklist:{client_ip }'
        try:
            if cache .get (blacklist_key ):
                return JsonResponse ({'error':'تم حظر هذا العنوان نهائيا','code':'IP_BLOCKED'},status =403 )
        except Exception as e:
            logger.error(f"WAF_CACHE_READ_FAILED | error={e}")

        try :
            from apps .security .models import BlockedIP ,BlockedDevice
            # ``enforceable()`` (not ``is_active=True``) so a block with an
            # ``expires_at`` in the past stops being enforced when it expires.
            blocked_ip =BlockedIP .objects .enforceable ().filter (ip_address =client_ip ).first ()
            if blocked_ip is not None :
                cache .set (blacklist_key ,True ,timeout =self ._block_cache_ttl (blocked_ip ))
                return JsonResponse ({'error':'تم حظر هذا العنوان نهائيا','code':'IP_BLOCKED'},status =403 )

            if device_fingerprint :
                dev_blacklist_key =f'waf_device_blacklist:{device_fingerprint }'
                if cache .get (dev_blacklist_key ):
                    return JsonResponse ({'error':'تم حظر هذا الجهاز','code':'DEVICE_BLOCKED'},status =403 )
                blocked_device =(
                BlockedDevice .objects .enforceable ()
                .filter (device_fingerprint =device_fingerprint )
                .first ()
                )
                if blocked_device is not None :
                    cache .set (dev_blacklist_key ,True ,timeout =self ._block_cache_ttl (blocked_device ))
                    return JsonResponse ({'error':'تم حظر هذا الجهاز','code':'DEVICE_BLOCKED'},status =403 )
        except Exception as e :
            logger.error(f"WAF_BLOCKLIST_CHECK_FAILED | error={e}")

            # Check request for attacks
        attack_detected =self ._detect_attacks (request )
        if attack_detected :
            return self ._block_request (request ,attack_detected )

        response =self .get_response (request )

        # Add security headers to response
        self ._add_security_headers (response )

        return response 

    def _detect_attacks (self ,request ):
        """Detect attack patterns in request."""
        from urllib .parse import unquote_plus
        # Combine all input sources (URL-decoded for accurate pattern matching)
        # Use unquote_plus to convert + to space (Django urlencode uses +)
        inputs_to_check =[
        unquote_plus (request .GET .urlencode ()),
        unquote_plus (request .POST .urlencode ()),
        ]

        inputs_to_check .extend (self ._scannable_body (request ))

        # Also check individual GET/POST values directly (already decoded by Django)
        for value in request .GET .dict ().values ():
            inputs_to_check .append (value )
        for value in request .POST .dict ().values ():
            inputs_to_check .append (value )

        inputs_to_check .append (unquote_plus (request .path ))

        # Headers are checked against all attack patterns EXCEPT SSRF.
        # SSRF patterns are URLs (e.g. http://localhost) and the Referer
        # header legitimately contains a same-origin URL, so scanning it
        # for those patterns produces false positives that block every
        # request from a legitimate browser front-end (incl. dev servers).
        # Real SSRF payloads live in parameters/body, which are fully
        # scanned above against every pattern group including SSRF.
        header_patterns ={
        attack_type :patterns 
        for attack_type ,patterns in self .compiled_patterns .items ()
        if attack_type !='SSRF'
        }
        suspicious_headers =['HTTP_USER_AGENT','HTTP_REFERER']
        for header in suspicious_headers :
            value =request .META .get (header ,'')
            if value :
                header_input =unquote_plus (value )
                for attack_type ,patterns in header_patterns .items ():
                    for pattern in patterns :
                        if pattern .search (header_input ):
                            return {
                            'type':attack_type ,
                            'pattern':pattern .pattern ,
                            'input_snippet':header_input [:200 ],
                            }

                            # Check each input against patterns
        for input_str in inputs_to_check :
            for attack_type ,patterns in self .compiled_patterns .items ():
                for pattern in patterns :
                    if pattern .search (input_str ):
                        return {
                        'type':attack_type ,
                        'pattern':pattern .pattern ,
                        'input_snippet':input_str [:200 ],
                        }

        return None

    def _body_text (self ,request ):
        """The request body as text, or '' when it should not be scanned.

        ``CONTENT_LENGTH`` is consulted *before* touching ``request.body``: for a
        file upload that attribute buffers the whole payload in memory (and
        raises ``RequestDataTooBig`` past ``DATA_UPLOAD_MAX_MEMORY_SIZE``), so a
        large body is left alone rather than read just to run regexes over it.
        """
        try :
            declared =int (request .META .get ('CONTENT_LENGTH')or 0 )
        except (TypeError ,ValueError ):
            declared =0
        if declared >MAX_BODY_SCAN_BYTES :
            return ''
        try :
            raw =request .body
        except Exception as e :
            logger .error (f"WAF_BODY_READ_FAILED | error={e }")
            return ''
        if not raw or len (raw )>MAX_BODY_SCAN_BYTES :
            return ''
        return raw .decode ('utf-8',errors ='ignore')

    def _scannable_body (self ,request ):
        """Strings from the body that are worth matching against the patterns.

        A multipart body is *not* scanned raw. Its closing delimiter is
        ``--<boundary>--``, and ``(--\\s*$)`` in SQL_INJECTION matched exactly
        that, so the WAF answered 403 WAF_BLOCKED to every ``multipart/form-data``
        request — every document, lab result and avatar upload, plus any
        form-encoded write. MIME framing is transport, not user input, so what is
        returned here is each non-file part's value (and each declared filename,
        which is attacker-controlled and worth checking for traversal). File
        *contents* are skipped: regexing a PDF or a JPEG yields false positives
        only.
        """
        from urllib .parse import unquote_plus

        text =self ._body_text (request )
        if not text :
            return []
        if (request .content_type or '').lower ()!='multipart/form-data':
            return [unquote_plus (text )]

        boundary =(request .content_params or {}).get ('boundary')
        if isinstance (boundary ,bytes ):
            boundary =boundary .decode ('latin-1',errors ='ignore')
        if not boundary :
            return []

        values =[]
        for part in text .split (f'--{boundary }'):
            headers ,sep ,payload =part .partition ('\r\n\r\n')
            if not sep :
                continue
            lowered =headers .lower ()
            filename =re .search (r'filename\s*=\s*"([^"]*)"',headers ,re .IGNORECASE )
            if filename :
                values .append (unquote_plus (filename .group (1 )))
            if 'filename'in lowered :
                continue
            values .append (unquote_plus (payload .rstrip ('\r\n')))
        return values

    def _block_request (self ,request ,attack_info ):
        """Block the malicious request and log it."""
        client_ip =self ._get_client_ip (request )

        logger .warning (
        f"WAF_BLOCKED | Type={attack_info ['type']} | "
        f"IP={client_ip } | Path={request .path } | "
        f"Pattern={attack_info ['pattern']} | "
        f"Input={attack_info ['input_snippet']}"
        )

        # Increment block counter for IP
        cache_key =f'waf_blocked:{client_ip }'
        blocked_count =cache .get (cache_key ,0 )+1 
        cache .set (cache_key ,blocked_count ,timeout =3600 )

        # If IP has too many blocks, add to blacklist
        if blocked_count >10 :
            blacklist_key =f'waf_blacklist:{client_ip }'
            cache .set (blacklist_key ,True ,timeout =86400 )# 24h
            logger .critical (
            f"IP_BLACKLISTED | IP={client_ip } | "
            f"Reason=repeated WAF violations ({blocked_count })"
            )

        return JsonResponse ({
        'error':'تم حظر الطلب من قبل جدار الحماية',
        'code':'WAF_BLOCKED',
        'attack_type':attack_info ['type'],
        },status =403 )

    def _add_security_headers (self ,response ):
        """Add security headers to response."""
        response ['X-Content-Type-Options']='nosniff'
        response ['X-Frame-Options']='DENY'
        response ['X-XSS-Protection']='1; mode=block'
        response ['Referrer-Policy']='same-origin'
        response ['Content-Security-Policy']=(
        "default-src 'self'; "
        # No 'unsafe-inline' for scripts: the built SPA loads every script as an
        # external module (verified against frontend/dist) and Vite emits no
        # inline bootstrap, so hash/nonce plumbing is not needed. React's inline
        # styling goes through the CSSOM (element.style.x = …), which CSP's
        # style-src does not gate — only <style> tags and style="" attributes
        # are, and the bundle contains none.
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "img-src 'self' data: blob: https:; "
        "font-src 'self' data: https://fonts.gstatic.com; "
        "connect-src 'self' ws: wss: https:; "
        "frame-ancestors 'none';"
        )
        response ['Strict-Transport-Security']=(
        'max-age=31536000; includeSubDomains; preload'
        )
        response ['Permissions-Policy']=(
        'geolocation=(), microphone=(self), camera=(self)'
        )
        return response 

    def _get_client_ip (self ,request ):
        """Delegate to the canonical resolver — see apps.core.net."""
        from apps .core .net import get_client_ip
        return get_client_ip (request )

    @staticmethod
    def _block_cache_ttl (block ,default =300 ):
        """How long a positive blocklist decision may be cached.

        A flat 86400 meant that lifting a block in the admin left the request
        path rejecting the caller for up to a day, and that a block expiring in
        five minutes kept rejecting them for the rest of the day. Cache for a
        short window, and never past the block's own expiry.
        """
        if block .expires_at is None :
            return default
        remaining =int ((block .expires_at -timezone .now ()).total_seconds ())
        return max (1 ,min (default ,remaining ))

    def _detect_device_type (self ,device_fingerprint :str )->str :
        """Detect device type from fingerprint prefix."""
        if not device_fingerprint :
            return 'unknown'
        prefixes ={
        'PC':'personal_computer',
        'MOB':'mobile',
        'TABLET':'tablet',
        'IOS':'ios',
        'AND':'android',
        'WEB':'web_client',
        }
        upper_fp =device_fingerprint .upper ()
        for prefix ,device_type in prefixes .items ():
            if upper_fp .startswith (prefix ):
                return device_type 
        return 'other'


class RateLimitMiddleware :
    """Additional rate limiting middleware for API endpoints.

    Fixed-window counter, 60 requests/minute per (IP, path). Two things it must
    not do, both of which it used to:

    * ``cache.set(key, count, timeout=60)`` on every request pushed the window's
      expiry forward each time, so a client that kept sending traffic never got a
      fresh window — once over the limit it stayed 429 indefinitely instead of
      recovering after a minute.
    * read-then-write on a shared counter loses increments under concurrency, and
      with a Redis cache shared across workers that is the normal case. ``add``
      followed by ``incr`` is atomic on the Redis backend, and ``incr`` leaves the
      existing TTL alone — which is exactly the fixed window we want.
    """

    LIMIT =60
    WINDOW =60

    def __init__ (self ,get_response ):
        self .get_response =get_response

    def __call__ (self ,request ):
        if request .path .startswith ('/api/'):
            client_ip =self ._get_client_ip (request )
            cache_key =f'ratelimit:{client_ip }:{request .path [:50 ]}'
            count =self ._hit (cache_key )

            # 60 requests per minute per endpoint
            if count >self .LIMIT :
                logger .warning (
                f"RATE_LIMIT_EXCEEDED | IP={client_ip } | "
                f"Path={request .path } | Count={count }"
                )
                response =JsonResponse ({
                'error':'تجاوز حد الطلبات المسموح',
                'code':'RATE_LIMIT_EXCEEDED',
                'retry_after':self .WINDOW ,
                },status =429 )
                response ['Retry-After']=str (self .WINDOW )
                return response

        return self .get_response (request )

    def _hit (self ,cache_key ):
        """Increment the window counter without extending its expiry."""
        try:
            if cache .add (cache_key ,1 ,timeout =self .WINDOW ):
                return 1
            try :
                return cache .incr (cache_key )
            except ValueError :
                # The window expired between ``add`` and ``incr``; start a new one.
                cache .set (cache_key ,1 ,timeout =self .WINDOW )
                return 1
        except Exception as e:
            logger.error(f"RATELIMIT_CACHE_FAILED | error={e}")
            return 1

    def _get_client_ip (self ,request ):
        """Delegate to the canonical resolver — see apps.core.net."""
        from apps .core .net import get_client_ip
        return get_client_ip (request )


class SessionSecurityMiddleware :
    """
    Validates that the current request's device fingerprint matches
    the active session fingerprint for the authenticated user to prevent token theft.

    Only session-authenticated requests reach the check here: on an API request
    ``request.user`` is still ``AnonymousUser`` at middleware time because DRF
    authenticates inside the view. That is why the same rule is enforced from
    ``BoundJWTAuthentication`` — this middleware alone was dead code for the JWT
    traffic it was written to protect.
    """

    def __init__ (self ,get_response ):
        self .get_response =get_response

    def __call__ (self ,request ):
    # We only check this if the user is authenticated
        user =getattr (request ,'user',None )
        if user is not None and user .is_authenticated :
            from apps .security .session_security import SessionManager
            # The session key is what register_session recorded for a
            # session-authenticated caller, so it scopes the fingerprint check to
            # this session instead of the union of the user's sessions — where an
            # evicted record read as a hijack and logged the whole account out.
            session =getattr (request ,'session',None )
            if SessionManager .reject_if_hijacked (
            user ,request ,session_id =getattr (session ,'session_key',None )
            ):
                return JsonResponse ({
                'error':'تم رصد نشاط مريب. يرجى تسجيل الدخول مرة أخرى.',
                'code':'SESSION_INVALIDATED'
                },status =401 )

        return self .get_response (request )


import uuid
from django.template.loader import render_to_string
from django.http import HttpResponse

class ZeroTrustConsentFirewallMiddleware:
    """
    Zero-Trust Network Access (ZTNA) Firewall with User Consent.
    Intercepts all requests. If the device/network combination is not approved,
    it either shows the consent HTML page (for browsers) or returns a 403 JSON (for API).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Exclude paths that are always public
        if request.path.startswith('/admin/') or request.path == '/health/' or request.path.startswith('/health/'):
            return self.get_response(request)

        # Exclude the ZTNA consent and status API paths
        if request.path in ['/api/v1/security/ztna-request/', '/api/v1/security/ztna-status/', '/api/v1/security/telegram-webhook/']:
            return self.get_response(request)

        # Exclude static/media files
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return self.get_response(request)

        from apps.core.net import get_client_ip
        client_ip = get_client_ip(request)
        
        # 1. Get fingerprint from Header (Android) or Cookie (Browser)
        fingerprint = request.META.get('HTTP_X_DEVICE_FINGERPRINT')
        is_new_cookie = False
        
        if not fingerprint:
            fingerprint = request.COOKIES.get('ztna_device_id')
            if not fingerprint:
                fingerprint = str(uuid.uuid4())
                is_new_cookie = True

        # 2. Check if approved in Redis
        # The approval is bound to BOTH fingerprint and IP address
        approval_key = f'ztna_approved_{fingerprint}_{client_ip}'
        is_approved = cache.get(approval_key)

        if is_approved:
            response = self.get_response(request)
            if is_new_cookie:
                response.set_cookie('ztna_device_id', fingerprint, max_age=60*60*24*365, httponly=True, samesite='Lax')
            return response

        # 3. Not approved => Block
        
        # If it's an API request (from Android or Javascript), return JSON
        if request.path.startswith('/api/'):
            response = JsonResponse({
                'error': 'الوصول مرفوض. يجب طلب صلاحية من الإدارة.',
                'code': 'ZTNA_BLOCKED',
                'fingerprint': fingerprint
            }, status=403)
            if is_new_cookie:
                response.set_cookie('ztna_device_id', fingerprint, max_age=60*60*24*365, httponly=True, samesite='Lax')
            return response

        # Otherwise, it's a browser requesting HTML. Render the Consent page.
        # We must set the cookie so the subsequent API call to ztna-request has it.
        try:
            html = render_to_string('ztna_consent.html')
            response = HttpResponse(html, status=403)
            if is_new_cookie:
                response.set_cookie('ztna_device_id', fingerprint, max_age=60*60*24*365, httponly=True, samesite='Lax')
            return response
        except Exception as e:
            logger.error(f"Failed to render ztna_consent.html: {e}")
            return JsonResponse({'error': 'ZTNA Blocked'}, status=403)
