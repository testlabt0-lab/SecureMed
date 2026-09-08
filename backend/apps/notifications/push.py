"""FCM HTTP v1 push delivery — no extra dependencies.

Sends through Google's FCM v1 API. Authentication uses the service-account
JSON: a signed JWT (RS256 via PyJWT, already a project dependency through
SimpleJWT) is exchanged at Google's OAuth endpoint for a short-lived bearer
token, which is cached in the shared cache until just before expiry.

Configuration (all optional — push stays silent when absent):

* ``FCM_PROJECT_ID``           — the Firebase project id.
* ``FCM_SERVICE_ACCOUNT_JSON`` — the service-account key as a JSON string, or a
  path to the file. The literal-string form suits container secrets; the path
  form suits a mounted volume.

Delivery is best-effort everywhere: a push outage must never fail the code
path that created the notification. Unregistered/invalid tokens deactivate
the stored row so the next send loop stops paying for them.
"""
import json
import logging
import time

import requests
from django.conf import settings
from django.core.cache import cache

from apps.notifications.models import PushToken

logger = logging.getLogger('security')

_OAUTH_URL = 'https://oauth2.googleapis.com/token'
_SEND_URL = 'https://fcm.googleapis.com/v1/projects/{project}/messages:send'
_SCOPE = 'https://www.googleapis.com/auth/firebase.messaging'
# Refresh a minute before expiry so an in-flight send never races the clock.
_TOKEN_TTL_MARGIN_SECONDS = 60


def push_configured():
    """True when both FCM settings are present."""
    return bool(
        getattr(settings, 'FCM_PROJECT_ID', '')
        and _service_account()
    )


def _service_account():
    """The parsed service-account key dict, or None."""
    raw = getattr(settings, 'FCM_SERVICE_ACCOUNT_JSON', '') or ''
    if not raw:
        return None
    if raw.strip().startswith('{'):
        try:
            return json.loads(raw)
        except (TypeError, ValueError):
            logger.error('FCM_SERVICE_ACCOUNT_JSON is not valid JSON')
            return None
    try:
        with open(raw, encoding='utf-8') as handle:
            return json.load(handle)
    except (OSError, ValueError):
        logger.error('FCM_SERVICE_ACCOUNT_JSON path could not be read: %s', raw)
        return None


def _access_token(service_account):
    """Bearer token from the service account, cached until near-expiry."""
    cache_key = f'fcm-oauth:{service_account.get("client_email", "?")}'
    cached = cache.get(cache_key)
    if cached:
        return cached

    import jwt  # PyJWT — already installed for SimpleJWT

    now = int(time.time())
    assertion = jwt.encode(
        {
            'iss': service_account['client_email'],
            'scope': _SCOPE,
            'aud': _OAUTH_URL,
            'iat': now,
            'exp': now + 3600,
        },
        service_account['private_key'],
        algorithm='RS256',
    )
    response = requests.post(
        _OAUTH_URL,
        data={
            'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
            'assertion': assertion,
        },
        timeout=10,
    )
    if response.status_code != 200:
        logger.error('FCM OAuth exchange failed: %s', response.text[:200])
        return None
    token = response.json().get('access_token')
    if not token:
        return None
    # Cache for the lifetime minus the safety margin.
    cache.set(cache_key, token, timeout=3600 - _TOKEN_TTL_MARGIN_SECONDS)
    return token


def send_push_to_token(token, title, body, data=None):
    """Send one message to one FCM token. Returns a status string."""
    service_account = _service_account()
    project = getattr(settings, 'FCM_PROJECT_ID', '')
    if not service_account or not project:
        return 'not_configured'

    access = _access_token(service_account)
    if not access:
        return 'auth_failed'

    payload = {
        'message': {
            'token': token,
            'notification': {'title': title, 'body': body},
            'data': {str(k): str(v) for k, v in (data or {}).items()},
            'android': {'priority': 'high'},
        }
    }
    try:
        response = requests.post(
            _SEND_URL.format(project=project),
            json=payload,
            headers={'Authorization': f'Bearer {access}'},
            timeout=10,
        )
    except requests.RequestException as exc:
        logger.warning('FCM send failed: %s', exc.__class__.__name__)
        return 'network_error'

    if response.status_code == 200:
        return 'sent'
    if response.status_code == 404:
        # UNREGISTERED — the app was uninstalled or the token rotated out.
        _deactivate_token(token)
        return 'unregistered'
    if response.status_code == 400:
        try:
            error = response.json().get('error', {}).get('details', [{}])[0]
            if error.get('errorCode', '').endswith('UNREGISTERED'):
                _deactivate_token(token)
                return 'unregistered'
        except (ValueError, IndexError, AttributeError):
            pass
        logger.warning('FCM rejected message: %s', response.text[:200])
        return 'rejected'
    logger.warning(
        'FCM send got HTTP %s: %s', response.status_code, response.text[:200]
    )
    return 'failed'


def send_push_to_user(user, title, body, data=None):
    """Deliver to every active token the user registered. Fire-and-forget."""
    if not user or not getattr(user, 'is_authenticated', True):
        return 0
    tokens = list(
        PushToken.objects.filter(user=user, is_active=True)
        .values_list('token', flat=True)[:10]
    )
    sent = 0
    for token in tokens:
        if send_push_to_token(token, title, body, data) == 'sent':
            sent += 1
    return sent


def _deactivate_token(token):
    PushToken.objects.filter(token=token).update(is_active=False)
