import subprocess
import time
import urllib.request
import os

# Start daphne
env = os.environ.copy()
env["DJANGO_SETTINGS_MODULE"] = "config.settings"
env["DEBUG"] = "False"
env["ALLOWED_HOSTS"] = "127.0.0.1,localhost,0.0.0.0"
# Set all required prod settings
env["SECRET_KEY"] = "test"
env["ENCRYPTION_KEY"] = "test"*8
env["AUDIT_LOG_HMAC_KEY"] = "test"*16
env["INITIAL_ADMIN_PASSWORD"] = "test12345"

p = subprocess.Popen(["daphne", "-b", "127.0.0.1", "-p", "8080", "config.asgi:application"], env=env, cwd="backend")
time.sleep(3)

# Make requests with curl to see raw response headers
print("--- TEST 1: GET /health/live/ ---")
subprocess.run(["curl", "-i", "http://127.0.0.1:8080/health/live/"])

print("\n--- TEST 2: GET /health/live ---")
subprocess.run(["curl", "-i", "http://127.0.0.1:8080/health/live"])

print("\n--- TEST 3: GET /health/ ---")
subprocess.run(["curl", "-i", "http://127.0.0.1:8080/health/"])

p.kill()
