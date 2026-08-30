#!/usr/bin/env bash
# ============================================================
# SecureMed — Render build step (web service)
# Installs Python deps and collects static files (whitenoise).
# The React SPA (frontend/dist) is pre-built and committed, so
# no Node build is needed on the server.
# ============================================================
set -euo pipefail
cd "$(dirname "$0")/../backend"

echo "==> Installing Python dependencies"
pip install --no-cache-dir -r requirements.txt

echo "==> Collecting static files"
python manage.py collectstatic --noinput

echo "==> Build complete"
