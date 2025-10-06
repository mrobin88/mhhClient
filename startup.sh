#!/bin/bash
# Azure App Service Startup Script for Django (root-level)

set -e

# Work in site root
cd /home/site/wwwroot

echo "Starting Django application setup..."

# Settings module
export DJANGO_SETTINGS_MODULE=config.simple_settings

echo "Running database migrations..."
python manage.py migrate --noinput --settings=config.simple_settings

echo "Collecting static files..."
python manage.py collectstatic --noinput --settings=config.simple_settings

echo "Setup complete. Starting Gunicorn..."
exec gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers 2 config.wsgi:application


