# ==========================================
# 1. Build Stage: Node.js (React/Vite)
# ==========================================
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy package files and install dependencies
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci

# Copy the rest of the frontend source code
COPY frontend/ ./

# Build the React app (outputs to /app/frontend/dist)
RUN npm run build


# ==========================================
# 2. Production Stage: Python (Django)
# ==========================================
FROM python:3.12-slim

WORKDIR /app

# Set environment variables for production
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBUG=False
# Port defaults to 8000, but Render might override it
ENV PORT=8000 

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir gunicorn psycopg2-binary whitenoise

# Copy backend source code
COPY backend/ ./backend/

# Copy the built React app from the frontend-builder stage
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Set the working directory to the backend so manage.py is accessible
WORKDIR /app/backend

# Collect static files (whitenoise will serve them).
#
# This has to run with DEBUG=False, because the runtime serves static assets through
# CompressedManifestStaticFilesStorage and that backend reads staticfiles.json — a
# manifest only produced by the DEBUG=False branch of STORAGES. Collecting with
# DEBUG=True would build the image happily and then raise "Missing staticfiles
# manifest entry" on the first template render.
#
# With DEBUG=False, though, settings.py requires SECRET_KEY with no fallback, and
# .dockerignore correctly keeps backend/.env out of the image — so the previous bare
# `RUN python manage.py collectstatic` aborted with
# `decouple.UndefinedValueError: SECRET_KEY not found` and this image could never
# finish building. settings.py also now raises ImproperlyConfigured at import time
# (not just a warning) if INITIAL_ADMIN_PASSWORD, DB_PASSWORD or AUDIT_LOG_HMAC_KEY
# are left at their insecure defaults, and collectstatic imports settings — so those
# also need a build-time-only value here (DB_ENGINE=sqlite sidesteps the DB_PASSWORD
# check entirely since it never reaches the Postgres branch). The values below exist
# only for the lifetime of this one layer (they are not ENV, so they are not in the
# final image config and not in the container environment); Railway injects the real
# values at start. They are deliberately not the placeholder defaults from
# settings.py, because those are on the reject list of the production configuration
# guard.
RUN SECRET_KEY="build-layer-only-not-a-runtime-secret" \
    ENCRYPTION_KEY="build-layer-only-not-a-runtime-secret" \
    INITIAL_ADMIN_PASSWORD="build-layer-only-not-a-runtime-secret" \
    DB_ENGINE="sqlite" \
    AUDIT_LOG_HMAC_KEY="build-layer-only-not-a-runtime-secret" \
    python manage.py collectstatic --noinput

# Drop root. devsecops/docker/Dockerfile.backend already did this; the image that is
# actually deployed did not, so a remote-code-execution bug in the app ran as uid 0
# with write access to the interpreter and every installed package.
#
# The chown has to come *after* collectstatic: settings.py creates backend/logs,
# backend/logs/emails and backend/media at import time, so they already exist here
# owned by root. Without this, the RotatingFileHandler for the 'security' logger opens
# logs/security.log for append as an unprivileged user and the container dies on
# startup with PermissionError. Everything the process writes at runtime — those two
# directories — lives under /app.
RUN useradd --create-home --shell /usr/sbin/nologin securemed \
    && chown -R securemed:securemed /app
USER securemed

# Liveness baked into the image, so any orchestrator (plain `docker`, Compose,
# k8s) — not only Render's healthCheckPath — can tell a wedged process from a
# healthy one. It hits /health/live/, the deliberately dependency-free 200 in
# apps.core.health.liveness, NOT /health/ready/: readiness touches DB/Redis/disk,
# and using it here would restart the container on any transient downstream blip.
# python, because the slim image has no curl; $PORT is read from the env, matching
# the daphne bind below. urlopen raises on refusal/5xx, which exits non-zero.
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import os,urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8000')+'/health/live/',timeout=4).status==200 else 1)"

# Copy start.sh and make it executable
COPY backend/start.sh ./start.sh
RUN chmod +x ./start.sh

# Served over ASGI, not WSGI. `gunicorn config.wsgi:application` was the previous
# command, and WSGI cannot carry a WebSocket handshake: every Channels consumer in
# this project (chat, notifications, video-call signalling) returned a protocol
# error in production while working locally under `runserver`, which is ASGI because
# 'daphne' is in INSTALLED_APPS. Daphne is used rather than gunicorn's uvicorn
# worker because it is already a dependency (via channels) and one async process
# suits the 0.5-CPU instance this deploys to. To scale out later, add
# `uvicorn[standard]` to requirements.txt and run:
#   gunicorn config.asgi:application -k uvicorn.workers.UvicornWorker \
#            --bind 0.0.0.0:$PORT --workers 4
CMD ["./start.sh"]
