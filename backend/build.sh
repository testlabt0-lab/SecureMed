#!/usr/bin/env bash
# exit on error
set -o errexit

echo "Building SecureMed Backend for Render..."
pip install -r requirements.txt

echo "Collecting static files..."
python manage.py collectstatic --no-input

echo "Running database migrations..."
python manage.py migrate

echo "Creating cache table if needed..."
python manage.py createcachetable securemed_cache_table

echo "Setting up initial roles and admin user..."
python manage.py setup_roles
python manage.py setup_initial_admin
