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
    """Verify AI service reachability."""
    import requests 
    ai_url =getattr (settings ,'AI_SERVICE_URL','http://localhost:8100')
    t0 =time .monotonic ()
    try :
        resp = requests.get(
            f'{ai_url}/health',
            headers={'User-Agent': 'SecureMed-HealthCheck/1.0'},
            timeout=3
        )
        latency_ms =round ((time .monotonic ()-t0 )*1000 ,2 )
        return {
        'status':'ok'if resp .status_code ==200 else 'degraded',
        'latency_ms':latency_ms ,
        'http_status':resp .status_code ,
        }
    except Exception as exc :
        return {'status':'degraded','detail':str (exc )}


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
    """
    checks ={
    'database':_check_database (),
    'redis':_check_redis (),
    'ai_service':_check_ai_service (),
    'disk':_check_disk (),
    'celery':_check_celery (),
    }

    # Comment_195
    statuses =[v ['status']for v in checks .values ()]
    if 'error'in statuses or 'critical'in statuses :
        overall ='unhealthy'
        http_code =503 
    elif 'degraded'in statuses or 'warning'in statuses :
        overall ='degraded'
        http_code =200 # Comment_196
    else :
        overall ='healthy'
        http_code =200 

    return JsonResponse ({
    'status':overall ,
    'service':'SecureMed API',
    'version':'2.0.0',
    'checks':checks ,
    'timestamp':time .strftime ('%Y-%m-%dT%H:%M:%SZ',time .gmtime ()),
    },status =http_code )
