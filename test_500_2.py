import os
import sys
import django
from django.test import Client

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ['DEBUG'] = 'False'
os.environ['DATABASE_URL'] = 'sqlite:///db.sqlite3'
os.environ['ALLOWED_HOSTS'] = '*'
os.environ['SECRET_KEY'] = 'test-secret-key-1234567890123456789012345678901234567890'
os.environ['ENCRYPTION_KEY'] = '12345678901234567890123456789012'
os.environ['AUDIT_LOG_HMAC_KEY'] = '12345678901234567890123456789012'

sys.path.append(os.path.join(os.getcwd(), 'backend'))

django.setup()

client = Client()
try:
    response = client.get('/', follow=True)
    print(f"Final Status Code: {response.status_code}")
    print(f"Content: {response.content.decode('utf-8')[:200]}")
except Exception as e:
    import traceback
    traceback.print_exc()
