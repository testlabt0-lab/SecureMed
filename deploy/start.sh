#!/usr/bin/env bash
# ============================================================
# SecureMed — Render start step (web service)
# 1. Applies DB migrations (Neon PostgreSQL or SQLite fallback)
# 2. Seeds demo data on first boot (idempotent get_or_create)
# 3. Starts gunicorn
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

echo "==> Starting gunicorn on port ${PORT:-8000}"
exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-1}" \
  --threads 8 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
