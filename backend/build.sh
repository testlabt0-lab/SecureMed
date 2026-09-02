#!/usr/bin/env bash
# exit on error
set -o errexit

echo "Building SecureMed Backend for Render..."
pip install -r requirements.txt

echo "Collecting static files..."
python manage.py collectstatic --no-input

echo "Running database migrations..."
python manage.py migrate
