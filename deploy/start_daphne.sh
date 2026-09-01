#!/usr/bin/env bash
# ============================================================
# SecureMed — Start script for WebSocket support (Daphne)
# Use this when you need WebSocket connections (real-time notifications)
# ============================================================
set -euo pipefail
cd "$(dirname "$0")/../backend"

# Render Blueprint injects AI_SERVICE_HOST (fromService.host) — build the URL
if [ -n "${AI_SERVICE_HOST:-}" ] && [ -z "${AI_SERVICE_URL:-}" ]; then
  export AI_SERVICE_URL="https://${AI_SERVICE_HOST}"
fi
echo "==> AI service URL: ${AI_SERVICE_URL:-<not set — AI features disabled>}"

# Password-reset links: default to the live Render URL (auto-injected by Render)
if [ -z "${FRONTEND_URL:-}" ] && [ -n "${RENDER_EXTERNAL_URL:-}" ]; then
  export FRONTEND_URL="${RENDER_EXTERNAL_URL}"
fi
echo "==> Frontend URL: ${FRONTEND_URL:-<not set — reset links will use localhost>}"

echo "==> Applying migrations"
python manage.py migrate --noinput

if [ "${SEED_DEMO_DATA:-1}" = "1" ]; then
  echo "==> Seeding demo data (idempotent — set SEED_DEMO_DATA=0 to disable)"
  python scripts/seed_data.py || echo "!! seed failed (continuing)"
fi

# Check if Redis is configured for WebSocket support
if [ -n "${REDIS_URL:-}" ]; then
  echo "==> Redis detected — starting Daphne for WebSocket support"
  exec daphne -b 0.0.0.0 -p ${PORT:-8000} config.asgi:application
else
  echo "==> WARNING: REDIS_URL not set — WebSocket features will use in-memory backend"
  echo "==> Starting Daphne (single-worker mode only without Redis)"
  exec daphne -b 0.0.0.0 -p ${PORT:-8000} config.asgi:application
fi
