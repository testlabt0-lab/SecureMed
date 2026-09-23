"""SPA catch-all serving for the single-service production topology.

Django serves the built React bundle. ``index.html`` is read off disk as a
plain file rather than rendered through the Django template engine: a Vite
build is not a Django template, and treating it as one risks ``{%``/``{{``
corruption in the bundle and hides a missing build behind a stale template
lookup (``TEMPLATES['DIRS']`` still points at a real dist from a previous
build, so ``TemplateView`` answers 200 for a shell that is not there).

Unknown paths under backend-owned prefixes (``/api/``, ``/admin/``, …) must
fall through to a real 404. Serving ``index.html`` for ``/api/v1/typo/``
turns every API typo into a 200 with an HTML body, which breaks API clients
that distinguish routing errors from successful responses and masks genuine
misconfiguration behind a page that renders.
"""
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404

# Path prefixes the SPA must never swallow. Each is owned by the backend or by
# an infrastructure probe; an unknown route under one of them is a client error
# and deserves a 404, not the app shell.
BACKEND_PREFIXES = (
    'api/',
    'admin/',
    'media/',
    'static/',
    'health',
    'metrics',
    'privacy/',
    'ws/',
)

INDEX_FILE = 'index.html'


def _index_path() -> Path:
    return Path(settings.FRONTEND_DIST) / INDEX_FILE


def serve_spa(request, path=''):
    """Serve the SPA shell for client-side routes.

    Mounted as the last URL pattern so every backend route is resolved first;
    the only requests that reach it are ones Django did not recognise, which
    is exactly the set a client-side router may handle.
    """
    if any(path.startswith(prefix) for prefix in BACKEND_PREFIXES):
        raise Http404('Unknown backend route')

    index = _index_path()
    if not index.is_file():
        # No frontend build present. Fails closed: answering with a stale shell
        # would render a blank page that looks like a healthy deployment.
        raise Http404('Frontend build is not available')

    # FileResponse streams the file, so a request never buffers the whole
    # bundle in memory.
    return FileResponse(index.open('rb'), content_type='text/html')
