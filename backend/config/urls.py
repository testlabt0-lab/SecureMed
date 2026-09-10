"""
URL configuration for SecureMed platform.

Production topology (single service):
  Django serves the API (/api/v1/*, AI included), admin, and the built React
  SPA (whitenoise assets + index.html catch-all). In development the Vite dev
  server proxies /api — same paths everywhere.

  There is no top-level /ai/ prefix: the AI endpoints are Django views under
  /api/v1/ai/ (apps.ai). The Node sidecar they used to proxy to is retired.
"""
from django .contrib import admin
from apps .accounts .views import (
AccountDeletionPageView ,AccountDeletionRequestView ,AccountDeletionConfirmView ,
)
from django .urls import path ,include ,re_path
from django .conf import settings
from django .conf .urls .static import static
from django .http import FileResponse ,JsonResponse ,Http404
from pathlib import Path
from apps .core .health import liveness ,readiness
from apps .core .media import ProtectedMediaView
from apps .core .metrics import metrics_view
from drf_spectacular .views import (
SpectacularAPIView ,
SpectacularSwaggerView ,
SpectacularRedocView ,
)


def health_check (request ):
    """Legacy health check endpoint — kept for backward compatibility."""
    return JsonResponse ({
    'status':'healthy',
    'service':'SecureMed API',
    'version':'2.0.0',
    })


def spa_view (request ):
    """Serve the built React SPA (single-service production deployment).

    Client-side routes (e.g. /patients/12) fall back to index.html so the
    router takes over. Backend prefixes (api/, admin/, static/, media/,
    health/, metrics) are excluded by the catch-all regex — they must never
    be swallowed by the SPA. `ai/` is no longer among them: nothing is
    mounted there since apps.ai moved under api/v1/, and an exclusion for a
    prefix Django does not serve turns any future client-side /ai/... route
    into a 404 on refresh.
    """
    index =Path (settings .FRONTEND_DIST )/'index.html'
    if index .exists ():
        resp =FileResponse (index .open ('rb'),content_type ='text/html; charset=utf-8')
        resp ['Cache-Control']='no-cache'# index.html must always revalidate
        return resp 
    raise Http404 ('Frontend build not found — run "npm run build" in frontend/')


urlpatterns =[
path ('admin/',admin .site .urls ),

# Health probes
path ('health/',health_check ,name ='health-check'),# legacy
path ('health/live/',liveness ,name ='health-liveness'),# Kubernetes livenessProbe
path ('health/ready/',readiness ,name ='health-readiness'),# Kubernetes readinessProbe

path ('api/v1/ai/',include ('apps.ai.urls')),
path ('metrics',metrics_view ,name ='prometheus-django-metrics'),

# API v1 routes
path ('api/v1/core/',include ('apps.core.urls')),
path ('api/v1/basins/',include ('apps.basins.urls')),
path ('api/v1/backups/',include ('apps.backups.urls')),
path ('api/v1/auth/',include ('apps.accounts.urls')),
# Play-mandated public web account deletion (4-3 §2) — browser pages, not API
# surface, so they live at the root with their own catch-all exclusion.
path ('privacy/account-deletion/',AccountDeletionPageView .as_view (),name ='account-deletion'),
path ('privacy/account-deletion/submit/',AccountDeletionRequestView .as_view (),name ='account-deletion-request'),
path ('privacy/account-deletion/confirm/',AccountDeletionConfirmView .as_view (),name ='account-deletion-confirm'),
path ('api/v1/channels/',include ('apps.channels.urls')),
path ('api/v1/patients/',include ('apps.patients.urls')),
path ('api/v1/security/',include ('apps.security.urls')),
path ('api/v1/audit/',include ('apps.audit.urls')),
path ('api/v1/notifications/',include ('apps.notifications.urls')),
path ('api/v1/analytics/',include ('apps.analytics.urls')),
path ('api/v1/reports/',include ('apps.reports.urls')),
path ('api/v1/appointments/',include ('apps.appointments.urls')),
path ('api/v1/pharmacy/',include ('apps.pharmacy.urls')),
path ('api/v1/billing/',include ('apps.billing.urls')),
path ('api/v1/lab/',include ('apps.lab.urls')),
path ('api/v1/wards/',include ('apps.wards.urls')),
path ('api/v1/telemedicine/',include ('apps.telemedicine.urls')),
path ('api/v1/interoperability/',include ('apps.interoperability.urls')),
]

# API documentation (Swagger / ReDoc)
# The generated schema is a complete map of every endpoint, parameter and role
# in the system. Publishing it anonymously on a PHI deployment hands an attacker
# the reconnaissance step for free, so it is opt-in outside DEBUG.
if getattr (settings ,'ENABLE_API_DOCS',settings .DEBUG ):
    urlpatterns +=[
    path ('api/schema/',SpectacularAPIView .as_view (),name ='schema'),
    path ('api/docs/',SpectacularSwaggerView .as_view (url_name ='schema'),name ='swagger-ui'),
    path ('api/redoc/',SpectacularRedocView .as_view (url_name ='schema'),name ='redoc'),
    ]

# Media: static() helper in DEBUG; explicit route in production
# Media is PHI. In DEBUG Django's own static serve is fine (local disk, local
# developer); in production every read goes through ProtectedMediaView, which
# authenticates the caller, authorises them against the owning channel and
# audits the access. PROTECT_MEDIA_FILES=False is the escape hatch for a
# deployment where an upstream proxy already enforces that.
#
# Both static() branches read straight off disk, bypassing the storage API, so they
# hand back AES-GCM ciphertext for anything written while ENCRYPT_MEDIA_AT_REST was
# on (see apps.core.storage). That combination is refused rather than left to produce
# files that download successfully and open as garbage — the failure mode is silent
# and looks like data corruption. ProtectedMediaView reads through the storage layer
# and decrypts, so the supported production route is unaffected.
_MEDIA_VIA_DISK =settings .DEBUG or not getattr (settings ,'PROTECT_MEDIA_FILES',True )
if _MEDIA_VIA_DISK and getattr (settings ,'ENCRYPT_MEDIA_AT_REST',False ):
    from django .core .exceptions import ImproperlyConfigured

    raise ImproperlyConfigured (
    'ENCRYPT_MEDIA_AT_REST is on while MEDIA_URL is served from disk '
    f'(DEBUG={settings .DEBUG }, '
    f'PROTECT_MEDIA_FILES={getattr (settings ,"PROTECT_MEDIA_FILES",True )}). '
    'Disk serving cannot decrypt: set ENCRYPT_MEDIA_AT_REST=False for local '
    'development, or leave PROTECT_MEDIA_FILES on so reads go through '
    'ProtectedMediaView.'
    )

if settings .DEBUG :
    urlpatterns +=static (settings .MEDIA_URL ,document_root =settings .MEDIA_ROOT )
elif getattr (settings ,'PROTECT_MEDIA_FILES',True ):
    urlpatterns +=[
    re_path (r'^media/(?P<path>.*)$',ProtectedMediaView .as_view (),name ='media-prod'),
    ]
else :
    urlpatterns +=static (settings .MEDIA_URL ,document_root =settings .MEDIA_ROOT )

# SPA catch-all — MUST stay last (excludes all backend prefixes above)
urlpatterns +=[
re_path (
r'^(?!api/|admin/|static/|media/|health/|metrics|privacy/).*$',
spa_view ,
name ='spa',
),
]
