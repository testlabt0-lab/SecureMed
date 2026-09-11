import os
import django
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ["DEBUG"] = "False"
django.setup()

print("DEBUG:", settings.DEBUG)
print("SECURE_SSL_REDIRECT:", getattr(settings, 'SECURE_SSL_REDIRECT', None))
print("SECURE_REDIRECT_EXEMPT:", getattr(settings, 'SECURE_REDIRECT_EXEMPT', None))
