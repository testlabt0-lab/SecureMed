"""Access-controlled Prometheus metrics endpoint.

``django_prometheus`` exposes per-view request counts and latencies, per-model
insert/update/delete counters and database connection stats. Published without a
guard — which is what ``path('', include('django_prometheus.urls'))`` did — that
is a free map of the deployment: which endpoints exist, how much PHI is being
written, and when. It is reconnaissance data, so it gets the same treatment as
any other internal surface.

Two ways in, both opt-in via settings:
  * ``METRICS_TOKEN`` — scrape with ``Authorization: Bearer <token>``.
  * ``METRICS_ALLOWED_IPS`` — networks allowed to scrape (loopback by default).
"""
import ipaddress
import logging
from secrets import compare_digest

from django.conf import settings
from django.http import HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django_prometheus.exports import ExportToDjangoView

from apps.core.net import get_client_ip

logger = logging.getLogger('security')


def _token_matches(request):
    expected = getattr(settings, 'METRICS_TOKEN', '')
    if not expected:
        return False
    header = request.META.get('HTTP_AUTHORIZATION', '')
    prefix = 'Bearer '
    if not header.startswith(prefix):
        return False
    return compare_digest(header[len(prefix):].strip(), expected)


def _ip_allowed(request):
    allowed = getattr(settings, 'METRICS_ALLOWED_IPS', None) or ['127.0.0.1', '::1']
    try:
        client = ipaddress.ip_address(get_client_ip(request))
    except ValueError:
        return False
    for entry in allowed:
        try:
            # Accepts both bare addresses and CIDR blocks (e.g. 10.0.0.0/8),
            # so a scrape job inside the cluster network can be allowed as one
            # entry instead of one line per pod.
            if client in ipaddress.ip_network(entry, strict=False):
                return True
        except ValueError:
            continue
    return False


def internal_access_allowed(request):
    """True when the caller may see internal operational detail.

    Shared with the detailed readiness probe in apps.core.health: both expose the
    same class of information (which dependencies exist, how they are performing,
    and verbatim connection errors), so both answer to the same gate instead of
    each inventing its own.
    """
    return _token_matches(request) or _ip_allowed(request)


@csrf_exempt
def metrics_view(request):
    """Serve /metrics to an authorised scraper only."""
    if internal_access_allowed(request):
        return ExportToDjangoView(request)

    logger.warning(
        'METRICS_ACCESS_DENIED ip=%s path=%s', get_client_ip(request), request.path
    )
    return HttpResponseForbidden('Forbidden')
