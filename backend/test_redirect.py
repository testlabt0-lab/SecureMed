import os
import django
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.test import RequestFactory
from django.middleware.security import SecurityMiddleware
import re

print("Exemptions:", getattr(settings, 'SECURE_REDIRECT_EXEMPT', []))

rf = RequestFactory()
req = rf.get('/health/live/')
req.META['HTTP_X_FORWARDED_PROTO'] = 'http'

mw = SecurityMiddleware(lambda req: django.http.HttpResponse("OK"))
resp = mw(req)
print(f"Status code: {resp.status_code}")
