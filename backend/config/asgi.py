import os 
from django .core .asgi import get_asgi_application 

os .environ .setdefault ('DJANGO_SETTINGS_MODULE','config.settings')

# Comment_424
# Comment_425
django_asgi_app =get_asgi_application ()

from channels .routing import ProtocolTypeRouter ,URLRouter 
from channels .auth import AuthMiddlewareStack 
import apps .notifications .routing 

application =ProtocolTypeRouter ({
"http":django_asgi_app ,
"websocket":AuthMiddlewareStack (
URLRouter (
apps .notifications .routing .websocket_urlpatterns 
)
),
})
