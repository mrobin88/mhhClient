#!/bin/bash
# Azure App Service Startup Script for Django
# This script runs automatically on container startup

# Set working directory - Azure deploys to /home/site/wwwroot
cd /home/site/wwwroot/backend || cd /home/site/wwwroot || exit 1

# Verify manage.py exists
if [ ! -f "manage.py" ]; then
    echo "ERROR: manage.py not found in $(pwd)"
    echo "Directory contents:"
    ls -la
    exit 1
fi

echo "Working directory: $(pwd)"
echo "Python version: $(python --version)"

# Set Django settings module
export DJANGO_SETTINGS_MODULE=config.settings

# Run migrations (with timeout to prevent hanging)
echo "Running database migrations..."
timeout 60 python manage.py migrate --noinput --settings=config.settings 2>&1 || {
    echo "WARNING: Migrations may have failed or were skipped"
}

# Start Gunicorn server
echo "Starting Gunicorn server..."
exec gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers 2 config.wsgi:application