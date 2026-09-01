"""
WAF (Web Application Firewall) middleware.

Security requirement #5: حماية قاعدة البيانات بأداة عازلة (DB Firewall)
Detects and blocks malicious requests: SQL injection, XSS, path traversal, etc.
"""
import re
import logging
from collections import defaultdict
from datetime import timedelta
from django.http import JsonResponse
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache

logger = logging.getLogger('security')

# Patterns that indicate an attack
ATTACK_PATTERNS = {
    'SQL_INJECTION': [
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
    'XSS': [
        r"(<script|</script|javascript:|onerror=|onload=|onmouse)",
        r"(<iframe|<embed|<object|<applet|<form)",
        r"(document\.cookie|document\.location|window\.location)",
        r"(\balert\s*\(|\bconfirm\s*\(|\bprompt\s*\()",
        r"(\beval\s*\(|\bexpression\s*\()",
        r"(<img[^>]+src\s*=|<body[^>]+onload)",
    ],
    'PATH_TRAVERSAL': [
        r"(\.\./|\.\.\\|/etc/passwd|/etc/shadow|/etc/hosts)",
        r"(c:\\windows\\system32|c:\\winnt)",
        r"(file://|php://|expect://)",
    ],
    'COMMAND_INJECTION': [
        r"(;\s*(ls|cat|pwd|id|whoami|uname|ifconfig|ping|wget|curl))",
        r"(\|\s*(ls|cat|pwd|id|whoami))",
        r"(`[^`]+`|\$\([^)]+\))",
        r"(&&\s*(ls|cat|pwd|id|whoami))",
    ],
    'XXE': [
        r"(<!ENTITY|<!DOCTYPE[^>]*\[)",
        r"(<\?xml.*\?>.*<!ENTITY)",
        r"(SYSTEM\s+[\"']file://)",
    ],
    'SSRF': [
        r"(http://localhost|https://localhost)",
        r"(http://127\.0\.0\.1|https://127\.0\.0\.1)",
        r"(http://169\.254\.169\.254|http://metadata)",
        r"(http://0\.0\.0\.0|https://0\.0\.0\.0)",
    ],
}


class WAFMiddleware:
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

    def __init__(self, get_response):
        self.get_response = get_response
        self.compiled_patterns = {
            attack_type: [re.compile(p, re.IGNORECASE) for p in patterns]
            for attack_type, patterns in ATTACK_PATTERNS.items()
        }

    def __call__(self, request):
        # Skip WAF for admin and health check
        if request.path.startswith('/admin/') or request.path == '/health/':
            return self.get_response(request)

        # Check request for attacks
        attack_detected = self._detect_attacks(request)
        if attack_detected:
            return self._block_request(request, attack_detected)

        response = self.get_response(request)

        # Add security headers to response
        self._add_security_headers(response)

        return response

    def _detect_attacks(self, request):
        """Detect attack patterns in request."""
        from urllib.parse import unquote_plus
        # Combine all input sources (URL-decoded for accurate pattern matching)
        # Use unquote_plus to convert + to space (Django urlencode uses +)
        inputs_to_check = [
            unquote_plus(request.GET.urlencode()),
            unquote_plus(request.POST.urlencode()),
        ]

        # Also check individual GET/POST values directly (already decoded by Django)
        for value in request.GET.dict().values():
            inputs_to_check.append(value)
        for value in request.POST.dict().values():
            inputs_to_check.append(value)

        # Check body for non-form requests
        if request.body and 'application/json' in request.content_type:
            try:
                body_str = request.body.decode('utf-8', errors='ignore')
                inputs_to_check.append(body_str)
            except Exception:
                pass

        # Check path (URL-decoded)
        inputs_to_check.append(unquote_plus(request.path))

        # Headers are checked against all attack patterns EXCEPT SSRF.
        # SSRF patterns are URLs (e.g. http://localhost) and the Referer
        # header legitimately contains a same-origin URL, so scanning it
        # for those patterns produces false positives that block every
        # request from a legitimate browser front-end (incl. dev servers).
        # Real SSRF payloads live in parameters/body, which are fully
        # scanned above against every pattern group including SSRF.
        header_patterns = {
            attack_type: patterns
            for attack_type, patterns in self.compiled_patterns.items()
            if attack_type != 'SSRF'
        }
        suspicious_headers = ['HTTP_USER_AGENT', 'HTTP_REFERER', 'HTTP_X_FORWARDED_FOR']
        for header in suspicious_headers:
            value = request.META.get(header, '')
            if value:
                header_input = unquote_plus(value)
                for attack_type, patterns in header_patterns.items():
                    for pattern in patterns:
                        if pattern.search(header_input):
                            return {
                                'type': attack_type,
                                'pattern': pattern.pattern,
                                'input_snippet': header_input[:200],
                            }

        # Check each input against patterns
        for input_str in inputs_to_check:
            for attack_type, patterns in self.compiled_patterns.items():
                for pattern in patterns:
                    if pattern.search(input_str):
                        return {
                            'type': attack_type,
                            'pattern': pattern.pattern,
                            'input_snippet': input_str[:200],
                        }

        return None

    def _block_request(self, request, attack_info):
        """Block the malicious request and log it."""
        client_ip = self._get_client_ip(request)

        logger.warning(
            f"WAF_BLOCKED | Type={attack_info['type']} | "
            f"IP={client_ip} | Path={request.path} | "
            f"Pattern={attack_info['pattern']} | "
            f"Input={attack_info['input_snippet']}"
        )

        # Increment block counter for IP
        cache_key = f'waf_blocked:{client_ip}'
        blocked_count = cache.get(cache_key, 0) + 1
        cache.set(cache_key, blocked_count, timeout=3600)

        # If IP has too many blocks, add to blacklist
        if blocked_count > 10:
            blacklist_key = f'waf_blacklist:{client_ip}'
            cache.set(blacklist_key, True, timeout=86400)  # 24h
            logger.critical(
                f"IP_BLACKLISTED | IP={client_ip} | "
                f"Reason=repeated WAF violations ({blocked_count})"
            )

        return JsonResponse({
            'error': 'تم حظر الطلب من قبل جدار الحماية',
            'code': 'WAF_BLOCKED',
            'attack_type': attack_info['type'],
        }, status=403)

    def _add_security_headers(self, response):
        """Add security headers to response."""
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'same-origin'
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "style-src-elem 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "img-src 'self' data: https:; "
            "font-src 'self' data: https://fonts.gstatic.com; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        response['Strict-Transport-Security'] = (
            'max-age=31536000; includeSubDomains; preload'
        )
        response['Permissions-Policy'] = (
            'geolocation=(), microphone=(), camera=()'
        )
        return response

    def _get_client_ip(self, request):
        """Get client IP from request."""
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            return x_forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '0.0.0.0')


class RateLimitMiddleware:
    """Additional rate limiting middleware for API endpoints."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/api/'):
            client_ip = self._get_client_ip(request)
            cache_key = f'ratelimit:{client_ip}:{request.path[:50]}'
            count = cache.get(cache_key, 0) + 1
            cache.set(cache_key, count, timeout=60)

            # 60 requests per minute per endpoint
            if count > 60:
                logger.warning(
                    f"RATE_LIMIT_EXCEEDED | IP={client_ip} | "
                    f"Path={request.path} | Count={count}"
                )
                return JsonResponse({
                    'error': 'تجاوز حد الطلبات المسموح',
                    'code': 'RATE_LIMIT_EXCEEDED',
                    'retry_after': 60,
                }, status=429)

        return self.get_response(request)

    def _get_client_ip(self, request):
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            return x_forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '0.0.0.0')


class DeviceFingerprintMiddleware:
    """
    Middleware to collect device fingerprint data for forensic analysis.
    
    This middleware captures detailed device information on every request,
    including:
    - MAC address (when available)
    - User-Agent and browser details
    - Screen resolution, timezone, language
    - Network information (IP, X-Forwarded headers)
    - Canvas fingerprint (if provided by frontend)
    - TLS fingerprint
    
    All data is stored for forensic evidence and can be used to identify
    and track malicious devices.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger('security.fingerprint')

    def __call__(self, request):
        # Skip fingerprinting for admin and health check endpoints
        if request.path.startswith('/admin/') or request.path == '/health/':
            return self.get_response(request)
        
        # Process fingerprint asynchronously to avoid blocking
        # Store fingerprint data in request for later use
        request.device_fp = None
        
        try:
            # Extract fingerprint data from request
            fingerprint_data = self._extract_fingerprint_data(request)
            
            # Get or create device fingerprint
            from apps.security.models import DeviceFingerprint
            fp, created = DeviceFingerprint.get_or_create_from_request(
                request, fingerprint_data
            )
            request.device_fp = fp
            
            # Log new devices for security monitoring
            if created:
                self.logger.info(
                    f"NEW_DEVICE | Hash={fp.fingerprint_hash[:16]}... | "
                    f"IP={fp.ip_address} | UA={fp.user_agent[:100] if fp.user_agent else 'N/A'}"
                )
            
            # Check if device is blacklisted
            if fp.is_blacklisted:
                self.logger.warning(
                    f"BLACKLISTED_DEVICE | Hash={fp.fingerprint_hash[:16]}... | "
                    f"IP={fp.ip_address} | Path={request.path}"
                )
                return JsonResponse({
                    'error': 'تم حظر هذا الجهاز',
                    'code': 'DEVICE_BLACKLISTED',
                }, status=403)
                
        except Exception as e:
            # Don't block requests if fingerprinting fails
            self.logger.error(f"FINGERPRINT_ERROR: {e}", exc_info=True)
        
        response = self.get_response(request)
        
        # Add fingerprint ID to response headers for debugging
        if hasattr(request, 'device_fp') and request.device_fp:
            response['X-Device-FP'] = request.device_fp.fingerprint_hash[:16]
        
        return response

    def _extract_fingerprint_data(self, request):
        """Extract fingerprint data from request."""
        import hashlib
        from django.utils import timezone
        
        # Parse User-Agent for browser/platform info
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        platform = 'Unknown'
        browser = 'Unknown'
        device_type = 'unknown'
        
        # Simple UA parsing (in production, use a library like ua-parser)
        ua_lower = user_agent.lower()
        if 'windows' in ua_lower:
            platform = 'Windows'
        elif 'mac os' in ua_lower or 'macos' in ua_lower:
            platform = 'macOS'
        elif 'linux' in ua_lower:
            platform = 'Linux'
        elif 'android' in ua_lower:
            platform = 'Android'
            device_type = 'mobile'
        elif 'iphone' in ua_lower or 'ipad' in ua_lower:
            platform = 'iOS'
            device_type = 'mobile' if 'iphone' in ua_lower else 'tablet'
        
        if 'chrome' in ua_lower and 'edg' not in ua_lower:
            browser = 'Chrome'
        elif 'firefox' in ua_lower:
            browser = 'Firefox'
        elif 'safari' in ua_lower and 'chrome' not in ua_lower:
            browser = 'Safari'
        elif 'edg' in ua_lower:
            browser = 'Edge'
        elif 'msie' in ua_lower or 'trident' in ua_lower:
            browser = 'Internet Explorer'
        
        # Check for bot patterns
        bot_patterns = ['bot', 'crawler', 'spider', 'scraper', 'curl', 'wget', 'python']
        if any(pattern in ua_lower for pattern in bot_patterns):
            device_type = 'bot'
        
        # Get fingerprint data from headers (sent by frontend JS)
        mac_address = request.META.get('HTTP_X_DEVICE_MAC', None)
        canvas_fingerprint = request.META.get('HTTP_X_CANVAS_FP', None)
        screen_resolution = request.META.get('HTTP_X_SCREEN_RES', None)
        timezone_offset = request.META.get('HTTP_X_TIMEZONE', None)
        language = request.META.get('HTTP_ACCEPT_LANGUAGE', '').split(',')[0]
        webrtc_ip = request.META.get('HTTP_X_WEBRTC_IP', None)
        tls_fingerprint = request.META.get('HTTP_X_TLS_FP', None)
        
        # Generate combined fingerprint hash
        hash_components = [
            user_agent,
            request.META.get('REMOTE_ADDR', ''),
            platform,
            browser,
            screen_resolution or '',
            timezone_offset or '',
            language,
            canvas_fingerprint or '',
        ]
        hash_source = '|'.join(hash_components)
        fingerprint_hash = hashlib.sha256(hash_source.encode()).hexdigest()
        
        # Build fingerprint data dict
        fingerprint_data = {
            'fingerprint_hash': fingerprint_hash,
            'mac_address': mac_address,
            'user_agent': user_agent[:500],  # Limit length
            'platform': platform,
            'browser': browser,
            'device_type': device_type,
            'screen_resolution': screen_resolution,
            'browser_timezone': timezone_offset,
            'language': language,
            'canvas_fingerprint': canvas_fingerprint,
            'webrtc_ip': webrtc_ip,
            'tls_fingerprint': tls_fingerprint,
            'metadata': {
                'path': request.path,
                'method': request.method,
                'timestamp': timezone.now().isoformat(),
            }
        }
        
        return fingerprint_data

    def _get_client_ip(self, request):
        """Get client IP from request."""
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            return x_forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '0.0.0.0')
