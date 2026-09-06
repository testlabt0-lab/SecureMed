#!/usr/bin/env bash
# ============================================================
# SecureMed — start step for a non-Docker host (web service)
#
# render.yaml does NOT use this file: it deploys `env: docker` with ./Dockerfile,
# runs migrations in `preDeployCommand` and starts Daphne from the image CMD. This
# script is the equivalent for a plain host (a VM, a bare Render "native runtime"
# service, a systemd unit) where nothing else runs those steps.
#
# 1. Applies DB migrations (PostgreSQL or SQLite fallback)
# 2. Collects static files — the runtime uses ManifestStaticFilesStorage, which
#    404s every asset until the manifest exists
# 3. Optionally seeds demo data (idempotent get_or_create)
# 4. Starts Daphne
# ============================================================
set -euo pipefail
cd "$(dirname "$0")/../backend"

# Password-reset and invitation links are built from FRONTEND_URL.
if [ -z "${FRONTEND_URL:-}" ] && [ -n "${RENDER_EXTERNAL_URL:-}" ]; then
  export FRONTEND_URL="${RENDER_EXTERNAL_URL}"
fi
echo "==> Frontend URL: ${FRONTEND_URL:-<not set — reset links will use localhost>}"

# AI: there is no sidecar to point at any more. The endpoints under /api/v1/ai/
# call Gemini in-process, so GEMINI_API_KEY is the whole configuration; without it
# the assistant reports itself unavailable and the rest of the app is unaffected.
if [ -n "${GEMINI_API_KEY:-}" ]; then
  echo "==> AI assistant: configured"
else
  echo "==> AI assistant: disabled (GEMINI_API_KEY not set)"
fi

# scripts/pre_migrate.py is a one-shot repair for databases predating the
# channels -> app_channels rename. It rewrites django_migrations, so it is opt-in
# (PRE_MIGRATE=1) and its exit status is no longer discarded with `|| true`: it
# used to run on every boot and swallow every error, which is how a broken
# history survived unnoticed.
if [ "${PRE_MIGRATE:-0}" != "0" ]; then
  echo "==> Repairing legacy migration history (PRE_MIGRATE is set)"
  python scripts/pre_migrate.py
fi

echo "==> Applying migrations"
# Plain `migrate`, matching render.yaml's preDeployCommand. It used to pass
# --fake-initial, which marks an initial migration as applied whenever its tables
# already exist — convenient for the legacy database this directory was written
# for, but it also hides a table that exists with the *wrong* shape. Legacy
# databases are handled by PRE_MIGRATE above, deliberately and once.
python manage.py migrate --noinput

echo "==> Collecting static files"
python manage.py collectstatic --noinput

if [ "${SEED_DEMO_DATA:-0}" = "1" ]; then
  echo "==> Seeding demo data (idempotent — unset SEED_DEMO_DATA to disable)"
  python scripts/seed_data.py || echo "!! seed failed (continuing)"
fi

echo "==> Starting Daphne ASGI server on port ${PORT:-8000}"
exec daphne -b 0.0.0.0 -p "${PORT:-8000}" config.asgi:application
