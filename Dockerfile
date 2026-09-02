# =============================================================================
#  SecureMed — Multi-stage Production Dockerfile
#  Stage 1: Build (dependencies compilation)
#  Stage 2: Runtime (minimal, non-root user)
# =============================================================================

# ─── Stage 1: Builder ────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# System deps needed for compilation only
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc g++ libpq-dev libffi-dev libssl-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps into a prefix (no cache, reproducible)
COPY backend/requirements.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt

# ─── Stage 2: Runtime ────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Security: create non-root user
RUN addgroup --system securemed && adduser --system --ingroup securemed --no-create-home securemed

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings \
    PATH="/install/bin:$PATH" \
    PYTHONPATH="/install/lib/python3.12/site-packages"

# Runtime system deps only (no compilers!)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /install

WORKDIR /app

# Copy source code
COPY backend/ /app/backend/
COPY frontend/dist/ /app/frontend/dist/

WORKDIR /app/backend

# Create runtime dirs with correct ownership
RUN mkdir -p logs/emails media staticfiles \
    && chown -R securemed:securemed /app

# Collect static files (runs as root before USER switch, so whitenoise can read them)
RUN python manage.py collectstatic --noinput --settings=config.settings 2>/dev/null || true

# Switch to non-root
USER securemed

EXPOSE 8000

# Liveness check (fast)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -sf http://localhost:8000/health/live/ || exit 1

# Gunicorn: 2 workers per CPU core (standard formula: 2*cores + 1)
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--worker-class", "sync", \
     "--timeout", "120", \
     "--keep-alive", "5", \
     "--log-level", "info", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
