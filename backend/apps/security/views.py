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
from django .utils import timezone
from django.core.cache import cache

from apps .security .permissions import IsAdmin ,IsAuditor 
from apps .security .models import BlockedDevice
from apps .security .blocklist_views import DeviceRegistrySerializer 
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

    @staticmethod
    def _audit_chain_verdict (days :int =2 )->dict :
        """Run AuditLog.verify_chain() over the recent window, never raising.

        The dashboard must render even if the chain read fails (a database
        hiccup should degrade the panel, not take the scan down with it).
        """
        try :
            from datetime import timedelta 
            from apps .audit .models import AuditLog 
            result =AuditLog .verify_chain (
            since =timezone .now ()-timedelta (days =days )
            )
            return {
            'ok':result ['ok'],
            'checked':result ['checked'],
            'signed':result ['signed'],
            'legacy':result ['legacy'],
            'unsigned':result ['unsigned'],
            'problems':len (result ['problems']),
            }
        except Exception as e :
            logger .error (f"Audit chain verdict failed: {e }")
            return {'ok':False ,'checked':0 ,'signed':0 ,'legacy':0 ,'unsigned':0 ,'problems':0 ,'error':True }

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
        # Live tamper-evidence verdict over the last 48h of audit rows — the
        # same window the daily verify-audit-chain Celery beat job checks, so
        # an operator sees in the UI what the 4 AM alert would have reported.
        # Computed over a bounded window because verify_chain() re-signs every
        # row it inspects; the full table grows without bound.
        'audit_chain_integrity':self ._audit_chain_verdict (),
        # Off-site backup delivery (Telegram document / S3 cloud copy).
        # Reported so the dashboard shows whether every archive actually
        # leaves the server or only lives in BACKUP_DIR.
        'backup_offsite_delivery':{
        'telegram_enabled':bool (getattr (settings ,'BACKUP_SEND_TO_TELEGRAM',False )),
        'telegram_ready':bool (
        getattr (settings ,'TELEGRAM_BOT_TOKEN','')and getattr (settings ,'TELEGRAM_ADMIN_CHAT_ID','')
        ),
        'cloud_enabled':bool (getattr (settings ,'BACKUP_OFFSITE_ENABLED',False )),
        'cloud_ready':bool (getattr (settings ,'BACKUP_OFFSITE_BUCKET','')),
        },
        # The webhook grants device approvals anonymously otherwise.
        'telegram_webhook_protected':bool (getattr (settings ,'TELEGRAM_WEBHOOK_SECRET','')),
        'media_access_controlled':bool (getattr (settings ,'PROTECT_MEDIA_FILES',True ))and not settings .DEBUG ,        # Uploaded files (imaging, lab reports, scanned documents) encrypted on disk
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


class MyDevicesView(APIView):
    """The caller's own registered devices, with self-service removal.

    The dashboard DeviceRegistryViewSet already exposes a filtered list, but
    that requires browsing the admin surface — the phone app needs one
    read-only endpoint for "أجهزتي" plus "إزالة جهازي" keyed by the device
    fingerprint the app already sends on every request, so no id lookup
    round-trip is needed.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps .security .models import DeviceRegistry 
        devices = DeviceRegistry.objects.filter(user=request.user)
        return Response({
            'devices': DeviceRegistrySerializer(devices, many=True).data,
        })

    def delete(self, request):
        from apps .security .models import DeviceRegistry 
        fingerprint = request.META.get('HTTP_X_DEVICE_FINGERPRINT', '')
        target_fp = request.data.get('device_fingerprint') or fingerprint
        if not target_fp:
            return Response(
                {'detail': 'device_fingerprint مطلوب'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        device = DeviceRegistry.objects.filter(
            user=request.user, device_fingerprint=target_fp,
        ).first()
        if device is None:
            return Response(
                {'detail': 'الجهاز غير موجود في حسابك'},
                status=status.HTTP_404_NOT_FOUND,
            )
        _deactivate_device(
            device, request, via='self', block=False, notify_owner=False,
        )
        return Response({
            'detail': 'تم إزالة الجهاز من حسابك — يمكنك طلب تفعيله مجدداً لاحقاً',
        })


class ActiveSessionsView(APIView):
    """List the caller's own live sessions, and end one of them.

    The session registry lives in the cache (SessionManager.register_session),
    so this reads the same shape it wrote: session_id, device_fingerprint,
    ip_address, timestamp. DELETE with `session_id` ends exactly that session
    (the same primitive `end_session` backs logout with) — لإنهاء جهاز محدد
    من مستخدم مسجل دخوله في مكان آخر.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from django.core.cache import cache
        sessions = cache.get(f'active_sessions:{request.user.id}', [])
        now = timezone.now().timestamp()
        return Response({
            'sessions': [
                {
                    'session_id': s.get('session_id', ''),
                    'device_fingerprint': s.get('device_fingerprint', ''),
                    'ip_address': s.get('ip_address', ''),
                    'started_at': s.get('timestamp'),
                    'age_minutes': int((now - s.get('timestamp', now)) // 60)
                    if s.get('timestamp') else None,
                }
                for s in sessions
            ],
            'count': len(sessions),
        })

    def delete(self, request):
        from apps.security.session_security import SessionManager
        from django.core.cache import cache

        session_id = str(request.data.get('session_id') or '').strip()
        if not session_id:
            # No session id = "end all my sessions", the same reading the
            # logout view gives a token-less logout. Invalidate every live
            # session this user has.
            cache_key = f'active_sessions:{request.user.id}'
            sessions = cache.get(cache_key, [])
            SessionManager.force_logout_user(request.user.id)
            log_security_event(
                user=request.user,
                event_type='SESSION_ENDED_BY_USER',
                request=request,
                details={'scope': 'all', 'count': len(sessions)},
            )
            return Response({'detail': 'تم إنهاء جميع الجلسات'})

        sessions = cache.get(f'active_sessions:{request.user.id}', [])
        if not any(
            str(s.get('session_id', '')) == session_id for s in sessions
        ):
            # Not refusing on an already-gone session: ending it is
            # idempotent, but a session id the user does not own must not
            # be endable — the ownership check above is the guard.
            return Response(
                {'detail': 'الجلسة غير موجودة أو انتهت بالفعل'},
                status=status.HTTP_404_NOT_FOUND,
            )
        SessionManager.end_session(request.user.id, session_id)
        log_security_event(
            user=request.user,
            event_type='SESSION_ENDED_BY_USER',
            request=request,
            details={'ended_session_id': session_id[:64]},
        )
        return Response({'detail': 'تم إنهاء الجلسة المحددة'})


class CheckDeviceView(APIView):
    """
    Pre-flight device authorization check.

    Outcomes are conveyed via a `state` field so clients can render the
    right message without pattern-matching on the localized `detail`:

    * `authorized` — the fingerprint matches a trusted DeviceRegistry row
                      holding a valid device license (ترخيص فعّال).
    * `unlicensed` — the device is trusted but its license is revoked,
                      suspended or expired: شاشة القفل تبقى ظاهرة. No
                      blacklist entry — إعادة الترخيص ترفع القفل فوراً.
    * `blocked`   — the fingerprint is on the BlockedDevice list (WAF still
                    enforces this independently; this answer is purely UX).
    * `pending`   — a DeviceRegistry row exists but is not yet trusted. The
                    user is told to wait for admin approval.
    * `unknown`   — the fingerprint is not on file and either no email was
                    supplied (the client must ask for one) or the email did
                    not match a real user (so we will not silently register a
                    device against a non-account). In both cases the client
                    should re-call this endpoint with `email` set.
    """
    permission_classes = [permissions.AllowAny]
    throttle_classes = []  # a per-scoped throttle is applied explicitly below
    throttle_scope = 'device_check'

    # Machine-readable counterpart of `state` so clients never have to
    # pattern-match the localized `detail` text.
    STATE_CODES = {
        'authorized': 'AUTHORIZED',
        'unlicensed': 'DEVICE_UNLICENSED',
        'blocked': 'DEVICE_BLOCKED',
        'pending': 'PENDING_DEVICE',
        'unknown': 'DEVICE_UNKNOWN',
    }

    def _state(self, kind, authorized, detail, **extra):
        body = {'state': kind, 'authorized': authorized, 'detail': detail,
                'code': self.STATE_CODES.get(kind, kind.upper())}
        body.update(extra)
        return body

    def post(self, request):
        fingerprint = (request.data.get('device_fingerprint')
                       or request.META.get('HTTP_X_DEVICE_FINGERPRINT', '')).strip()
        mac_address = (request.data.get('mac_address')
                       or request.META.get('HTTP_X_MAC_ADDRESS', '')).strip()
        email = (request.data.get('email') or '').strip().lower() or None

        if not fingerprint:
            return Response(self._state('unknown', False, 'معرف الجهاز مطلوب'),
                            status=status.HTTP_400_BAD_REQUEST)
        if len(fingerprint) > 255:
            return Response(self._state('unknown', False, 'معرف الجهاز طويل جداً'),
                            status=status.HTTP_400_BAD_REQUEST)

        # Per-device throttle: a single client making thousands of requests
        # against one fingerprint must not be able to spam Telegram. Done here
        # rather than via DRF's scope throttle because the key is the
        # fingerprint, not the IP, and the rate lives under the same name so
        # the throttle is visible in the operator's settings.
        from django.core.cache import cache
        rate_key = f'device_check:{fingerprint}'
        recent = cache.get(rate_key, 0) + 1
        cache.set(rate_key, recent, timeout=60)
        if recent > 10:
            return Response(self._state('pending', False, 'كثرة المحاولات، يرجى الانتظار قليلاً'),
                            status=status.HTTP_429_TOO_MANY_REQUESTS)

        from apps.security.models import DeviceRegistry, BlockedDevice
        from apps.accounts.models import User
        from apps.core.net import get_client_ip

        if BlockedDevice.objects.enforceable().filter(device_fingerprint=fingerprint).exists():
            return Response(self._state('blocked', False, 'هذا الجهاز محظور'),
                            status=status.HTTP_403_FORBIDDEN)

        user = User.objects.filter(email=email).first() if email else None

        device = DeviceRegistry.objects.filter(device_fingerprint=fingerprint).first()

        if device is not None:
            if device.is_trusted:
                # License gate (متطلب د. مجد): الثقة وحدها لا ترفع شاشة
                # القفل — الجهاز يحتاج ترخيصاً فعّالاً. الأجهزة الموثوقة
                # السابقة تُرخَّص تلقائياً مرة واحدة (lazy provisioning)
                # ثم يصبح الإلغاء قرار إدارة من تلجرام أو اللوحة.
                from apps.security import licensing
                license_obj = licensing.ensure_device_license(device)
                if license_obj is not None and license_obj.is_valid:
                    return Response(self._state(
                        'authorized', True, 'الجهاز مصرح ومرخص',
                        licensed=True,
                        license_status=license_obj.effective_status,
                        license_expires_at=(
                            license_obj.expires_at.isoformat()
                            if license_obj.expires_at else None
                        ),
                    ))
                # Trusted-but-unlicensed: lock, don't blacklist. Audited so
                # the admin sees repeated denial attempts in the audit trail
                # (throttled upstream to 10/min per fingerprint).
                log_security_event(
                    user=device.user,
                    event_type='DEVICE_UNLICENSED_ACCESS',
                    request=request,
                    details={
                        'device_id': str(device.id),
                        'device_fingerprint': fingerprint,
                        'mac_address': mac_address,
                        'license_status': (
                            license_obj.effective_status if license_obj else 'MISSING'
                        ),
                    },
                    severity='WARNING',
                )
                status_label = (
                    license_obj.effective_status if license_obj else 'غير موجود'
                )
                return Response(self._state(
                    'unlicensed', False,
                    f'الجهاز غير مرخص (حالة الترخيص: {status_label}). '
                    f'يرجى التواصل مع الإدارة لتفعيل الترخيص.',
                    licensed=False,
                    license_status=(
                        license_obj.effective_status if license_obj else 'MISSING'
                    ),
                ), status=status.HTTP_403_FORBIDDEN)
            return Response(self._state('pending', False,
                                        'الجهاز غير مصرح، بانتظار موافقة الإدارة'),
                            status=status.HTTP_403_FORBIDDEN)

        # Unknown fingerprint. We never register a device row without a
        # matching user account: a DeviceRegistry.user FK to nothing would
        # either crash the insert or orphan the row, and an attacker calling
        # this endpoint with random fingerprints would otherwise pollute the
        # admin's Telegram. Returning `unknown` lets the client ask the user
        # for an email and retry.
        if user is None:
            return Response(self._state('unknown', False,
                                        'الجهاز غير معروف. يرجى إدخال بريدك الإلكتروني لطلب التفعيل.'),
                            status=status.HTTP_403_FORBIDDEN)

        # get_or_create, not create: two parallel requests from the same new
        # device would otherwise collide on the (user, device_fingerprint)
        # unique constraint and 500 the user.
        device, _ = DeviceRegistry.objects.get_or_create(
            user=user,
            device_fingerprint=fingerprint,
            defaults={
                'mac_address': mac_address,
                'os_info': request.META.get('HTTP_X_OS_INFO', ''),
                'browser_info': request.META.get('HTTP_X_BROWSER_INFO', ''),
                'last_ip_address': get_client_ip(request),
                'is_trusted': False,
            },
        )

        log_security_event(
            user=user,
            event_type='DEVICE_REGISTRATION_REQUESTED',
            request=request,
            details={'device_id': str(device.id), 'device_fingerprint': fingerprint},
            severity='INFO',
        )

        # Acknowledge the request inside the app as well — the request itself
        # only reaches the admin chat, which the user cannot see.
        _notify_user(
            user,
            notification_type='LOGIN_ALERT',
            title='وصلنا طلب تفعيل جهازك',
            message=(
                f'استلمنا طلب تفعيل جهاز ({request.META.get("HTTP_X_OS_INFO", "جهاز")} — '
                f'بصمة: {fingerprint[:16]}…) وأُرسل للإدارة للموافقة. '
                f'ستصلك رسالة عند اتخاذ القرار.'
            ),
            priority='MEDIUM',
            data={'device_id': str(device.id)},
        )

        # Telegram is best-effort. A failure here must not 500 the response:
        # the device is already recorded as pending and the admin can still
        # approve from the dashboard.
        try:
            from apps.security.telegram_service import send_device_approval_request
            send_device_approval_request(device)
            telegram_sent = True
        except Exception as e:
            logger.error(f"Failed to send device approval Telegram: {e}")
            telegram_sent = False

        detail = ('تم إرسال طلب تفعيل للإدارة (تيليجرام ولوحة التحكم)'
                  if telegram_sent else
                  'الجهاز غير مصرح، يرجى التواصل مع الإدارة للتفعيل')
        return Response(self._state('pending', False, detail),
                        status=status.HTTP_403_FORBIDDEN)


def _notify_user(user, notification_type, title, message, priority='HIGH', data=None):
    """In-app (+email per preferences) notification to the affected user.

    Wrapped best-effort: a notifications outage must not fail the security
    action that triggered it. Emails respect the user's preferences through
    apps.notifications.utils.send_notification.
    """
    try:
        from apps.notifications.utils import send_notification
        send_notification(
            recipient=user,
            notification_type=notification_type,
            priority=priority,
            title=title,
            message=message,
            data=data or {},
            send_email=True,
        )
    except Exception as e:
        logger.error(f"Failed to notify user {getattr(user, 'id', '?')}: {e}")


def _deactivate_device(device, request, via, block=True, notify_owner=True):
    """Revoke a trusted device: untrust + (optionally) block + audit.

    Shared by the Telegram `deactivate_` callback and the dashboard API so
    both paths enforce one deactivation rule — إلغاء التفعيل. ``block=False``
    is the self-service path: the owner removes their own device (trust gone,
    its session killed) but the device is not blacklisted, so they may request
    activation for it again later. The block reuses the same BlockedDevice row
    shape as a Telegram reject, so the WAF enforces it identically.
    """
    device.is_trusted = False
    device.save(update_fields=['is_trusted'])

    # سحب الترخيص مع إلغاء التفعيل — القاعدة الموحدة (متطلب د. مجد):
    # جهاز غير مفعّل لا يبقى مرخصاً. الإشعار المخصص للترخيص مكتوم لأن
    # إشعار إلغاء التفعيل أدناه يكفي، وتدقيق الترخيص يبقى مسجلاً.
    from apps.security import licensing
    licensing.deactivate_license(device, via=via, request=request, notify_owner=False)

    from apps.security.models import BlockedDevice
    if block:
        BlockedDevice.objects.update_or_create(
            device_fingerprint=device.device_fingerprint,
            defaults={
                'reason': f'إلغاء تفعيل ({via})',
                'mac_address': device.mac_address,
                'is_active': True,
            },
        )
    else:
        # A prior block would defeat "I may re-request activation later".
        BlockedDevice.objects.filter(
            device_fingerprint=device.device_fingerprint, is_active=True,
        ).delete()

    # Invalidate the "not blocked" caches so the change is enforced on the
    # very next request. device_tracker.is_device_blocked caches a negative
    # answer for 5 minutes and the WAF keeps its own positive-decision cache.
    try:
        from django.core.cache import cache
        cache.delete(f'blocked_device:{device.device_fingerprint}:{device.mac_address or ""}')
        cache.delete(f'waf_device_blacklist:{device.device_fingerprint}')
    except Exception as e:
        logger.error(f"Deactivation cache invalidation failed: {e}")

    from apps.security.session_security import SessionManager
    SessionManager.force_logout_user(device.user_id)

    # The owner must learn their device was revoked from inside the app too,
    # not only from the admin chat — otherwise they discover it the next time
    # the lock screen refuses them. A self-deactivation needs no notification:
    # the user did it themselves.
    if notify_owner:
        _notify_user(
            device.user,
            notification_type='SECURITY_ALERT',
            title='تم إلغاء تفعيل أحد أجهزتك',
            message=(
                f'أُلغي تفعيل الجهاز ({device.os_info or "جهاز"} — '
                f'بصمة: {device.device_fingerprint[:16]}…) بواسطة الإدارة ({via}) '
                f'وأُضيف للقائمة السوداء. إن لم تكن أنت من طلب ذلك تواصل مع الإدارة فوراً.'
            ),
            priority='HIGH',
            data={'device_id': str(device.id), 'via': via},
        )

    event_type = ('DEVICE_DEACTIVATED_VIA_TELEGRAM'
                  if via == 'telegram' else 'DEVICE_DEACTIVATED')
    log_security_event(
        user=device.user,
        event_type=event_type,
        request=request,
        details={'device_id': str(device.id),
                 'device_fingerprint': device.device_fingerprint,
                 'mac_address': device.mac_address,
                 'via': via,
                 'blocked': block},
        severity='WARNING',
    )

    # Best-effort heads-up to the admin chat when the deactivation came from
    # the dashboard, so both control surfaces stay visible in one place.
    if via != 'telegram':
        try:
            from apps.security.telegram_service import (
                send_device_deactivated_notification,
            )
            by_label = {'dashboard': 'لوحة الإدارة',
                        'self': 'مالك الجهاز (ذاتياً)'}.get(via, via)
            send_device_deactivated_notification(device, by_label=by_label)
        except Exception as e:
            logger.error(f"Failed to notify deactivation via Telegram: {e}")


class TelegramWebhookView(APIView):
    """
    Receives approve/reject/deactivate callbacks from the admin Telegram bot.

    This endpoint grants login access, so it must verify that the request
    actually came from Telegram. Two complementary controls:

    * `X-Telegram-Bot-Api-Secret-Token` header is matched against
      `TELEGRAM_WEBHOOK_SECRET` (Telegram sends it when the webhook was
      registered with `setWebhook(secret_token=...)`).
    * the `chat_id` in the callback is compared to `TELEGRAM_ADMIN_CHAT_ID`,
      so even an attacker who guesses a valid callback id cannot replay an
      approval from a chat they control.

    If `TELEGRAM_WEBHOOK_SECRET` is unset the endpoint refuses everything —
    an open callback endpoint is strictly worse than a broken one.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        expected = getattr(settings, 'TELEGRAM_WEBHOOK_SECRET', '')
        if not expected:
            logger.error('Telegram webhook called but TELEGRAM_WEBHOOK_SECRET is not configured')
            return Response({'ok': False}, status=status.HTTP_403_FORBIDDEN)
        provided = request.META.get('HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN', '')
        if not provided or provided != expected:
            logger.warning('Telegram webhook rejected: missing or wrong secret token')
            return Response({'ok': False}, status=status.HTTP_403_FORBIDDEN)

        from apps.security.telegram_service import answer_callback_query, edit_message_text
        from apps.security.models import DeviceRegistry, BlockedDevice

        update = request.data
        # Text commands (مثل /pending، /users) go through the shared console
        # processor — the same one the polling command feeds, so both paths
        # authorize and act identically.
        if update.get('message'):
            from apps.security.telegram_bot import process_update
            process_update(update, request)
            return Response({'ok': True})

        callback_query = update.get('callback_query')
        if not callback_query:
            # Telegram also pings the webhook with the same endpoint on
            # setWebhook(); respond OK so its health check is happy.
            return Response({'ok': True})

        admin_chat_id = str(getattr(settings, 'TELEGRAM_ADMIN_CHAT_ID', '') or '')
        message = callback_query.get('message') or {}
        chat_id = str((message.get('chat') or {}).get('id', ''))
        if admin_chat_id and chat_id and chat_id != admin_chat_id:
            logger.warning(f'Telegram webhook callback from non-admin chat {chat_id}')
            return Response({'ok': False}, status=status.HTTP_403_FORBIDDEN)

        callback_id = callback_query.get('id', '')
        data = callback_query.get('data', '')
        message_id = message.get('message_id')
        original_text = message.get('text', '')

        try:
            if data.startswith('approve_'):
                device_id = data[len('approve_'):]
                device = DeviceRegistry.objects.filter(id=device_id).first()
                if device is None:
                    answer_callback_query(callback_id, 'الجهاز غير موجود', show_alert=True)
                else:
                    device.is_trusted = True
                    device.save(update_fields=['is_trusted'])
                    log_security_event(
                        user=device.user,
                        event_type='DEVICE_APPROVED_VIA_TELEGRAM',
                        request=request,
                        details={'device_id': str(device.id),
                                 'device_fingerprint': device.device_fingerprint},
                        severity='INFO',
                    )
                    _notify_user(
                        device.user,
                        notification_type='LOGIN_ALERT',
                        title='تم تفعيل جهاز جديد',
                        message=(
                            f'تمت الموافقة على الجهاز ({device.os_info or "جهاز"} — '
                            f'بصمة: {device.device_fingerprint[:16]}…) ويمكنك تسجيل الدخول منه الآن. '
                            f'إن لم تكن أنت من طلبه فأبلغ الإدارة فوراً.'
                        ),
                        priority='MEDIUM',
                        data={'device_id': str(device.id)},
                    )
                    answer_callback_query(callback_id, 'تم تفعيل الجهاز بنجاح')
                    if message_id is not None:
                        edit_message_text(chat_id, message_id,
                                          f"{original_text}\n\n✅ <b>تم تفعيل الجهاز</b>")

            elif data.startswith('deactivate_'):
                # إلغاء التفعيل: revoke a previously-trusted device. The device
                # stops passing CheckDeviceView, is added to the WAF blocklist
                # (same as a Telegram reject), and the user's cached session is
                # force-ended so a stolen token on the revoked device dies with
                # the tap of the button.
                device_id = data[len('deactivate_'):]
                device = DeviceRegistry.objects.filter(id=device_id).first()
                if device is None:
                    answer_callback_query(callback_id, 'الجهاز غير موجود', show_alert=True)
                else:
                    _deactivate_device(device, request, via='telegram')
                    answer_callback_query(callback_id, 'تم إلغاء تفعيل الجهاز وحظره')
                    if message_id is not None:
                        edit_message_text(chat_id, message_id,
                                          f"{original_text}\n\n🔒 <b>تم إلغاء التفعيل وحظر الجهاز</b>")

            elif data.startswith('reject_'):
                device_id = data[len('reject_'):]
                device = DeviceRegistry.objects.filter(id=device_id).first()
                if device is None:
                    answer_callback_query(callback_id, 'الجهاز غير موجود', show_alert=True)
                else:
                    BlockedDevice.objects.update_or_create(
                        device_fingerprint=device.device_fingerprint,
                        defaults={
                            'reason': 'مرفوض من تيليجرام',
                            'mac_address': device.mac_address,
                            'is_active': True,
                        },
                    )
                    log_security_event(
                        user=device.user,
                        event_type='DEVICE_REJECTED_VIA_TELEGRAM',
                        request=request,
                        details={'device_id': str(device.id),
                                 'device_fingerprint': device.device_fingerprint},
                        severity='WARNING',
                    )
                    _notify_user(
                        device.user,
                        notification_type='SECURITY_ALERT',
                        title='تم رفض طلب تفعيل جهاز',
                        message=(
                            f'رُفض الجهاز ({device.os_info or "جهاز"} — '
                            f'بصمة: {device.device_fingerprint[:16]}…) وحُظر من الدخول. '
                            f'إن كنت أنت من حاول الدخول فتواصل مع الإدارة لمعرفة السبب.'
                        ),
                        priority='HIGH',
                        data={'device_id': str(device.id)},
                    )
                    answer_callback_query(callback_id, 'تم حظر الجهاز')
                    if message_id is not None:
                        edit_message_text(chat_id, message_id,
                                          f"{original_text}\n\n❌ <b>تم حظر الجهاز</b>")

            elif data.startswith('ztna_approve_'):
                req_id = data[len('ztna_approve_'):]
                req_data = cache.get(f'ztna_pending_{req_id}')
                if not req_data:
                    answer_callback_query(callback_id, 'انتهت صلاحية الطلب', show_alert=True)
                else:
                    fingerprint = req_data['fingerprint']
                    # Key shape must match the middleware's check
                    # (ztna_approved_{fingerprint}, no IP suffix) — a stale
                    # write here means the السماح button "does nothing".
                    cache.set(f'ztna_approved_{fingerprint}', True, timeout=None)
                    cache.delete(f'ztna_pending_{req_id}')
                    answer_callback_query(callback_id, 'تمت الموافقة وتفعيل الوصول')
                    if message_id is not None:
                        edit_message_text(chat_id, message_id,
                                          f"{original_text}\n\n✅ <b>تمت الموافقة وتم فك الحظر عن الشبكة</b>")

            elif data.startswith('ztna_reject_'):
                req_id = data[len('ztna_reject_'):]
                req_data = cache.get(f'ztna_pending_{req_id}')
                if not req_data:
                    answer_callback_query(callback_id, 'انتهت صلاحية الطلب', show_alert=True)
                else:
                    fingerprint = req_data['fingerprint']
                    client_ip = req_data['ip']
                    BlockedDevice.objects.update_or_create(
                        device_fingerprint=fingerprint,
                        defaults={
                            'reason': 'حظر ZTNA من تيليجرام',
                            'is_active': True,
                        }
                    )
                    cache.set(f'waf_device_blacklist:{fingerprint}', True, timeout=None)
                    cache.set(f'waf_blacklist:{client_ip}', True, timeout=None)
                    cache.delete(f'ztna_pending_{req_id}')
                    answer_callback_query(callback_id, 'تم حظر الجهاز والشبكة نهائياً')
                    if message_id is not None:
                        edit_message_text(chat_id, message_id,
                                          f"{original_text}\n\n❌ <b>تم حظر الجهاز والشبكة</b>")
            else:
                answer_callback_query(callback_id, 'إجراء غير معروف', show_alert=True)
        except Exception as e:
            logger.error(f"Telegram webhook handler error: {e}")
            try:
                answer_callback_query(callback_id, 'خطأ في المعالجة', show_alert=True)
            except Exception:
                pass
            return Response({'ok': False})

        return Response({'ok': True})

import uuid

class ZTNARequestView(APIView):
    permission_classes = [permissions.AllowAny]
    # Deliberately no DRF throttles: the default AnonRateThrottle (20/hour)
    # keys on REMOTE_ADDR, which behind Render's proxy is one shared address
    # for every visitor — the status poller alone burns the whole bucket in
    # about two minutes and every later consent click 429s silently. The
    # per-fingerprint cap below is the anti-spam control instead.
    authentication_classes = []
    throttle_classes = []

    RATE_LIMIT = 3
    RATE_WINDOW = 600

    def post(self, request):
        from apps.core.net import get_client_ip

        fingerprint = request.data.get('fingerprint') or request.COOKIES.get('ztna_device_id')
        # The approval key the middleware checks is built from
        # get_client_ip(), so the pending record must carry the same
        # resolution — a raw X-Forwarded-For leftmost value never matches and
        # a Telegram "allow" would unlock nothing.
        ip = get_client_ip(request)

        if not fingerprint:
            return Response({'error': 'Missing fingerprint'}, status=400)

        rate_key = f'ztna_req_rate:{fingerprint}'
        recent = cache.get(rate_key, 0) + 1
        cache.set(rate_key, recent, timeout=3600)
        if recent > self.RATE_LIMIT:
            return Response(
                {'error': 'تم إرسال طلبك مسبقاً. يرجى انتظار موافقة الإدارة.'},
                status=429,
            )

        req_id = str(uuid.uuid4())
        cache.set(f'ztna_pending_{req_id}', {'fingerprint': fingerprint, 'ip': ip}, timeout=3600)

        # The result must be honest: a visitor told "sent" while Telegram was
        # never configured waits for a message that never arrives.
        telegram_sent = False
        telegram_error = ''
        bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
        chat_id = getattr(settings, 'TELEGRAM_ADMIN_CHAT_ID', '')

        import html as _html
        from apps.security.netinfo import MAC_SOURCE_LABELS, peer_profile

        peer = peer_profile(request)
        ip_display = peer['ip'] + (' (محلي — نفس جهاز الخادم)' if peer['is_loopback'] else '')
        mac_note = MAC_SOURCE_LABELS.get(peer['mac_source'], '')
        lines = [
            '🔐 <b>طلب وصول جديد ZTNA</b>',
            '',
            '<b>الجهاز:</b>',
            f"• بصمة الجهاز: <code>{_html.escape(fingerprint)}</code>",
        ]
        if peer['platform']:
            lines.append(f"• نظام التشغيل: {_html.escape(peer['platform'])}")
        if peer['user_agent']:
            lines.append(f"• المتصفح: <code>{_html.escape(peer['user_agent'][:80])}</code>")
        lines += [
            '',
            '<b>الشبكة:</b>',
            f"• عنوان IP: <code>{_html.escape(ip_display)}</code>",
            f"• عنوان MAC: <code>{_html.escape(peer['mac'] or 'غير متاح')}</code>"
            + (f" — {_html.escape(mac_note)}" if mac_note else ''),
        ]
        if peer['lan_hint']:
            lines.append(
                f"• عناوين الخادم على الشبكة المحلية: <code>{_html.escape(peer['lan_hint'])}</code>"
            )
        if not peer['mac'] and not peer['is_private']:
            lines.append(
                '• <i>ملاحظة: عنوان MAC لا يُنقل عبر الراوترات — يتوفر فقط لزوار '
                'الشبكة المحلية نفسها أو من تطبيق الأندرويد الذي يرسله مع الطلب.</i>'
            )
        text = '\n'.join(lines)

        if bot_token and chat_id:
            import requests
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "reply_markup": {
                    "inline_keyboard": [
                        [{"text": "✅ السماح بالدخول", "callback_data": f"ztna_approve_{req_id}"}],
                        [{"text": "❌ حظر نهائي", "callback_data": f"ztna_reject_{req_id}"}]
                    ]
                }
            }
            try:
                tg_response = requests.post(url, json=payload, timeout=5)
                telegram_sent = tg_response.status_code == 200
                if not telegram_sent:
                    telegram_error = f'telegram_http_{tg_response.status_code}'
                    logger.error(
                        f"ZTNA telegram send failed: {tg_response.status_code} "
                        f"{tg_response.text[:200]}"
                    )
            except Exception as e:
                telegram_error = 'telegram_unreachable'
                logger.error(f"Error sending ZTNA request to telegram: {e}")
        else:
            telegram_error = 'telegram_not_configured'
            logger.error(
                "ZTNA request dropped: TELEGRAM_BOT_TOKEN / "
                "TELEGRAM_ADMIN_CHAT_ID not configured"
            )

        message = (
            'تم إرسال طلبك للإدارة. يرجى إبقاء الصفحة مفتوحة لحين الموافقة.'
            if telegram_sent else
            'تعذر إرسال الطلب للإدارة حالياً. يرجى المحاولة لاحقاً أو التواصل مع الإدارة.'
        )
        body = {
            'message': message,
            'req_id': req_id,
            'telegram_sent': telegram_sent,
        }
        if telegram_error:
            body['telegram_error'] = telegram_error
        return Response(body)

class ZTNAStatusView(APIView):
    permission_classes = [permissions.AllowAny]
    # Polled every few seconds by the waiting consent page — the shared
    # anonymous throttle would starve it (see ZTNARequestView).
    authentication_classes = []
    throttle_classes = []

    def get(self, request):
        from apps.core.net import get_client_ip

        fingerprint = request.query_params.get('fingerprint') or request.COOKIES.get('ztna_device_id')
        ip = get_client_ip(request)

        if not fingerprint:
            return Response({'error': 'Missing fingerprint'}, status=400)

        is_approved = cache.get(f'ztna_approved_{fingerprint}')
        if is_approved:
            return Response({'status': 'approved'})
            
        is_blocked = cache.get(f'waf_device_blacklist:{fingerprint}') or cache.get(f'waf_blacklist:{ip}')
        if is_blocked:
            return Response({'status': 'rejected'})
            
        return Response({'status': 'pending'})


