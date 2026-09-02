"""
WAF (Web Application Firewall) middleware.

Security requirement #5: حماية قاعدة البيانات بأداة عازلة (DB Firewall)
Detects and blocks malicious requests: SQL injection, XSS, path traversal, etc.
"""
import re
import logging
import json
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

        client_ip = self._get_client_ip(request)
        device_fingerprint = request.META.get('HTTP_X_DEVICE_FINGERPRINT', '')
        
        # 1. Check IP Blacklist (cache first, then DB)
        blacklist_key = f'waf_blacklist:{client_ip}'
        if cache.get(blacklist_key):
            return JsonResponse({'error': 'تم حظر هذا العنوان نهائيا'}, status=403)
            
        try:
            from apps.security.models import BlockedIP, BlockedDevice
            if BlockedIP.objects.filter(ip_address=client_ip, is_active=True).exists():
                cache.set(blacklist_key, True, timeout=86400)
                return JsonResponse({'error': 'تم حظر هذا العنوان نهائيا'}, status=403)
                
            if device_fingerprint:
                dev_blacklist_key = f'waf_device_blacklist:{device_fingerprint}'
                if cache.get(dev_blacklist_key) or BlockedDevice.objects.filter(device_fingerprint=device_fingerprint, is_active=True).exists():
                    cache.set(dev_blacklist_key, True, timeout=86400)
                    return JsonResponse({'error': 'تم حظر هذا الجهاز'}, status=403)
        except Exception as e:
            # DB might not be ready during migrations
            pass

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
        try:
            if 'application/json' in (request.content_type or '') and request.body:
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
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "img-src 'self' data: blob: https:; "
            "font-src 'self' data: https://fonts.gstatic.com; "
            "connect-src 'self' ws: wss: https:; "
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

    def _detect_device_type(self, device_fingerprint: str) -> str:
        """Detect device type from fingerprint prefix."""
        if not device_fingerprint:
            return 'unknown'
        prefixes = {
            'PC': 'personal_computer',
            'MOB': 'mobile',
            'TABLET': 'tablet',
            'IOS': 'ios',
            'AND': 'android',
            'WEB': 'web_client',
        }
        upper_fp = device_fingerprint.upper()
        for prefix, device_type in prefixes.items():
            if upper_fp.startswith(prefix):
                return device_type
        return 'other'


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


class SessionSecurityMiddleware:
    """
    Validates that the current request's device fingerprint matches 
    the active session fingerprint for the authenticated user to prevent token theft.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # We only check this if the user is authenticated
        if request.user and request.user.is_authenticated:
            current_fingerprint = request.META.get('HTTP_X_DEVICE_FINGERPRINT', '')
            if current_fingerprint:
                # Get the user's registered fingerprint from cache
                cache_key = f'active_sessions:{request.user.id}'
                sessions = cache.get(cache_key, [])
                
                # Check if current fingerprint is in the list of active sessions
                valid = False
                for session in sessions:
                    if session.get('device_fingerprint') == current_fingerprint:
                        valid = True
                        break
                        
                if sessions and not valid:
                    # Token is being used from a different device than it was issued for
                    logger.warning(
                        f"SESSION_HIJACK_ATTEMPT | User={request.user.id} | "
                        f"Expected={sessions[-1].get('device_fingerprint')} | "
                        f"Actual={current_fingerprint}"
                    )
                    
                    # Force logout
                    from apps.security.session_security import SessionManager
                    SessionManager.force_logout_user(request.user.id)
                    
                    return JsonResponse({
                        'error': 'تم رصد نشاط مريب. يرجى تسجيل الدخول مرة أخرى.',
                        'code': 'SESSION_INVALIDATED'
                    }, status=401)
                    
        return self.get_response(request)
