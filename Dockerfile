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

# Collect static files (whitenoise will serve them)
RUN python manage.py collectstatic --noinput

# Run Gunicorn
CMD gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 4 --threads 2 --timeout 60
