# ============================================================
# SecureMed — single-container production image (optional
# alternative to the Render blueprint's native runtimes).
#
#   docker build -t securemed .
#   docker run -p 8000:8000 \
#     -e DATABASE_URL=postgresql://...?sslmode=require \
#     -e SECRET_KEY=... -e AI_SERVICE_URL=http://host:8100 \
#     securemed
#
# The AI microservice runs separately:
#   cd ai-service && npm install && node server.js
# ============================================================
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings

WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Backend code + pre-built SPA (frontend/dist committed to the repo)
COPY backend /app/backend
COPY frontend/dist /app/frontend/dist

WORKDIR /app/backend
RUN python manage.py collectstatic --noinput

EXPOSE 8000
CMD ["bash", "../deploy/start.sh"]
