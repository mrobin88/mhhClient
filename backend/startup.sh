#!/bin/bash
# Azure App Service Startup Script for Django

set -e  # Exit on any error

# Set the working directory
cd /home/site/wwwroot

echo "Starting Django application setup..."

# Set Django settings module
export DJANGO_SETTINGS_MODULE=backend.config.production_settings

# Run database migrations
echo "Running database migrations..."
python backend/manage.py migrate --noinput --settings=backend.config.production_settings

# Collect static files
echo "Collecting static files..."
python backend/manage.py collectstatic --noinput --settings=backend.config.production_settings

echo "Setup complete. Starting Gunicorn..."

# Start Gunicorn with exec to replace the shell process
exec gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers 2 backend.config.wsgi:application