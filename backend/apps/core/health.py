"""
Detailed health check endpoint for SecureMed.
Used by load balancers, Kubernetes probes, and monitoring systems.

Endpoints:
  GET /health/          → quick liveness (always fast)
  GET /health/detailed/ → full readiness check (DB, Redis, AI, disk, queue)
"""
import os 
import shutil 
import time 
import logging 
from django .http import JsonResponse 
from django .db import connection 
from django .core .cache import cache 
from django .conf import settings 

logger =logging .getLogger (__name__ )


def _check_database ():
    """Verify database connectivity and response time."""
    t0 =time .monotonic ()
    try :
        with connection .cursor ()as cur :
            cur .execute ("SELECT 1")
        latency_ms =round ((time .monotonic ()-t0 )*1000 ,2 )
        return {'status':'ok','latency_ms':latency_ms }
    except Exception as exc :
        return {'status':'error','detail':str (exc )}


def _check_redis ():
    """Verify Redis connectivity (used for cache + Celery broker)."""
    t0 =time .monotonic ()
    try :
        cache .set ('_health_check','1',timeout =5 )
        val =cache .get ('_health_check')
        if val !='1':
            return {'status':'error','detail':'Cache read/write mismatch'}
        latency_ms =round ((time .monotonic ()-t0 )*1000 ,2 )
        return {'status':'ok','latency_ms':latency_ms }
    except Exception as exc :
        return {'status':'degraded','detail':str (exc )}


def _check_ai_service ():
    """Report whether the AI module can answer.

    This used to open an HTTP connection to AI_SERVICE_URL/health — a Node
    microservice that no longer exists: the AI endpoints call Gemini in-process
    (apps.ai.views). The probe therefore reported 'degraded' forever in every
    deployment and spent up to 3 seconds per readiness check waiting for a
    connection to 127.0.0.1:8100 to be refused. What a caller actually needs to
    know is whether the module is configured, which is a settings lookup.
    """
    configured =bool (getattr (settings ,'GEMINI_API_KEY',''))
    return {
    'status':'ok'if configured else 'degraded',
    'configured':configured ,
    'provider':'google-generativeai (in-process)',
    'detail':''if configured else 'GEMINI_API_KEY is not set — AI features are disabled',
    }


def _check_disk ():
    """Check available disk space."""
    try :
        total ,used ,free =shutil .disk_usage ('/')
        free_gb =round (free /(1024 **3 ),2 )
        used_pct =round (used /total *100 ,1 )
        status ='ok'
        if used_pct >90 :
            status ='critical'
        elif used_pct >80 :
            status ='warning'
        return {
        'status':status ,
        'free_gb':free_gb ,
        'used_percent':used_pct ,
        }
    except Exception as exc :
        return {'status':'error','detail':str (exc )}


def _check_celery ():
    """Check if Celery workers are responsive."""
    try :
        from celery .app .control import Inspect 
        from config .celery import app as celery_app 
        i =Inspect (app =celery_app ,timeout =1.0 )
        ping =i .ping ()
        if ping :
            worker_count =len (ping )
            return {'status':'ok','active_workers':worker_count }
        return {'status':'degraded','detail':'No Celery workers responded'}
    except Exception as exc :
        return {'status':'degraded','detail':str (exc )}


def liveness (request ):
    """
    Lightweight liveness probe.
    Returns 200 immediately — only fails if the process is dead.
    Used by: Docker healthcheck, Kubernetes livenessProbe.
    """
    return JsonResponse ({
    'status':'alive',
    'service':'SecureMed API',
    'version':'2.0.0',
    })


def readiness (request ):
    """
    Full readiness check.
    Returns 200 only when ALL critical dependencies are healthy.
    Used by: load balancers, Kubernetes readinessProbe.

    The per-check detail is not public. `checks` carries database latency, disk
    usage, worker counts and — via `str(exc)` — verbatim driver errors, which for a
    connection failure include the database host, port and user. That is a free
    infrastructure map for an unauthenticated caller. The status code still tells a
    load balancer everything it needs (200 vs 503) without a body, so only a caller
    that passes the same gate as /metrics gets the breakdown.
    """
    checks ={
    'database':_check_database (),
    'redis':_check_redis (),
    'ai_service':_check_ai_service (),
    'disk':_check_disk (),
    'celery':_check_celery (),
    }

    # Determine overall status
    statuses =[v ['status']for v in checks .values ()]
    if 'error'in statuses or 'critical'in statuses :
        overall ='unhealthy'
        http_code =503
    elif 'degraded'in statuses or 'warning'in statuses :
        overall ='degraded'
        http_code =200 # still serving traffic — just warn
    else :
        overall ='healthy'
        http_code =200

    payload ={
    'status':overall ,
    'service':'SecureMed API',
    'version':'2.0.0',
    'timestamp':time .strftime ('%Y-%m-%dT%H:%M:%SZ',time .gmtime ()),
    }

    from apps .core .metrics import internal_access_allowed
    _user =getattr (request ,'user',None )
    if internal_access_allowed (request )or getattr (_user ,'is_staff',False ):
        payload ['checks']=checks
    else :
        # Which dependency is unhealthy is itself useful to an attacker, so the
        # anonymous view is limited to the names of the checks that ran.
        payload ['checked']=sorted (checks )

    return JsonResponse (payload ,status =http_code )
