# -*- coding: utf-8 -*-
"""ZTNA flow smoke test against the LIVE Render backend.

IMPORTANT: the ZTNA-protected Django service is https://securemed-web.onrender.com
(securemed.onrender.com is a different Flask app — requests sent there go nowhere).
"""
import requests
import uuid

BASE = "https://securemed-web.onrender.com"

# 1. Homepage must answer 403 with the consent page and set the device cookie
s = requests.Session()
r = s.get(f"{BASE}/", timeout=90)
print("Homepage:", r.status_code, "| consent page:", "ZTNA" in r.text, "| cookie set:", bool(s.cookies.get("ztna_device_id")))

# 2. Consent click — Telegram delivery is now reported honestly
fp = f"PC-{uuid.uuid4()}"
r2 = s.post(f"{BASE}/api/v1/security/ztna-request/", json={"fingerprint": fp}, timeout=90)
print("ztna-request:", r2.status_code, r2.text[:300])

# 3. Status while pending
r3 = s.get(f"{BASE}/api/v1/security/ztna-status/", timeout=90)
print("ztna-status:", r3.status_code, r3.text[:200])
