import os
import django
from django.conf import settings
from django.test import Client

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ["DEBUG"] = "False"
os.environ["ALLOWED_HOSTS"] = "*"
os.environ["ENCRYPTION_KEY"] = "12345678901234567890123456789012"
os.environ["INITIAL_ADMIN_PASSWORD"] = "123"
os.environ["AUDIT_LOG_HMAC_KEY"] = "123"
django.setup()

client = Client()
response = client.get('/health/live/', HTTP_HOST='securemed.railway.app')
print(f"Status Code: {response.status_code}")
if response.status_code in [301, 302, 307, 308]:
    print(f"Redirect to: {response.url}")
