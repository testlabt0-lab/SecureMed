#!/bin/bash
set -e

# Wait for postgres
if [ "$DATABASE_URL" != "" ] && [[ "$DATABASE_URL" == postgres* ]]; then
    echo "Waiting for postgres..."
    # A simple sleep or using netcat
    sleep 5
fi

# Apply database migrations
echo "Apply database migrations"
python manage.py migrate

# Create cache table if using DB cache
if [ "$CACHE_BACKEND" == "django.core.cache.backends.db.DatabaseCache" ]; then
    python manage.py createcachetable || true
fi

# Collect static files
echo "Collect static files"
python manage.py collectstatic --noinput

# Start server
echo "Starting server"
exec daphne -b 0.0.0.0 -p 8000 config.asgi:application
