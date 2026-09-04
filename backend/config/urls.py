"""
URL configuration for SecureMed platform.

Production topology (single service):
  Django serves the API (/api/v1/*), the AI proxy (/ai/*), admin, and the
  built React SPA (whitenoise assets + index.html catch-all). In development
  the Vite dev server proxies /api and /ai instead — same paths everywhere.
"""
from django .contrib import admin 
from django .urls import path ,include ,re_path 
from django .conf import settings 
from django .conf .urls .static import static 
from django .http import FileResponse ,JsonResponse ,Http404 
from pathlib import Path 
from apps .core .health import liveness ,readiness 
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


def _serve_media (request ,path ):
    """Serve user-uploaded media in production (demo-scale traffic)."""
    from django .views .static import serve 
    return serve (request ,path ,document_root =settings .MEDIA_ROOT )


def spa_view (request ):
    """Serve the built React SPA (single-service production deployment).

    Client-side routes (e.g. /patients/12) fall back to index.html so the
    router takes over. Backend prefixes (api/, admin/, static/, media/,
    health/, ai/) are excluded by the catch-all regex — they must never
    be swallowed by the SPA.
    """
    index =Path (settings .FRONTEND_DIST )/'index.html'
    if index .exists ():
        resp =FileResponse (index .open ('rb'),content_type ='text/html; charset=utf-8')
        resp ['Cache-Control']='no-cache'# Comment_562
        return resp 
    raise Http404 ('Frontend build not found — run "npm run build" in frontend/')


urlpatterns =[
path ('admin/',admin .site .urls ),

# Comment_563
path ('health/',health_check ,name ='health-check'),# Comment_564
path ('health/live/',liveness ,name ='health-liveness'),# Comment_565
path ('health/ready/',readiness ,name ='health-readiness'),# Comment_566

path ('api/v1/ai/',include ('apps.ai.urls')),

# Comment_568
path ('api/v1/basins/',include ('apps.basins.urls')),
path ('api/v1/backups/',include ('apps.backups.urls')),
path ('api/v1/auth/',include ('apps.accounts.urls')),
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

# Comment_569
path ('api/schema/',SpectacularAPIView .as_view (),name ='schema'),
path ('api/docs/',SpectacularSwaggerView .as_view (url_name ='schema'),name ='swagger-ui'),
path ('api/redoc/',SpectacularRedocView .as_view (url_name ='schema'),name ='redoc'),
]

# Comment_570
if settings .DEBUG :
    urlpatterns +=static (settings .MEDIA_URL ,document_root =settings .MEDIA_ROOT )
else :
    urlpatterns +=[
    re_path (r'^media/(?P<path>.*)$',_serve_media ,name ='media-prod'),
    ]

    # Comment_571
urlpatterns +=[
re_path (
r'^(?!api/|admin/|static/|media/|health/|ai/).*$',
spa_view ,
name ='spa',
),
]
