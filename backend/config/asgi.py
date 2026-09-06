import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# The Django ASGI application must be built before importing anything that
# touches the app registry (consumers import models), so keep this first.
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.security.websocket import AllowedHostsOriginValidator  # noqa: E402

from apps.security.channels_auth import JWTAuthMiddlewareStack  # noqa: E402
import apps.notifications.routing  # noqa: E402
import apps.telemedicine.routing  # noqa: E402

# AllowedHostsOriginValidator rejects sockets whose Origin is not in ALLOWED_HOSTS.
# Without it any page on the internet could open an authenticated socket in a
# logged-in user's browser — the WebSocket handshake is exempt from CORS, so this
# check is the only thing standing in for it.
#
# JWTAuthMiddlewareStack, not AuthMiddlewareStack: the SPA and the Android app
# authenticate with Bearer tokens and never hold a Django session, so session-only
# auth left every real client anonymous. See apps/security/channels_auth.py.
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        JWTAuthMiddlewareStack(
            URLRouter(
                apps.notifications.routing.websocket_urlpatterns
                + apps.telemedicine.routing.websocket_urlpatterns
            )
        )
    ),
})
