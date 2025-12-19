#!/bin/bash
# Azure App Service Startup Script for Django
# Fast startup - starts Gunicorn immediately

# Navigate to backend directory (handle both deployment structures)
cd /home/site/wwwroot 2>/dev/null || cd /opt/startup 2>/dev/null || true

# If backend subdirectory exists, use it
if [ -d "backend" ] && [ -f "backend/manage.py" ]; then
    cd backend
elif [ ! -f "manage.py" ] && [ -d "backend" ]; then
    cd backend
fi

# Verify we're in the right place
if [ ! -f "manage.py" ]; then
    echo "ERROR: manage.py not found in $(pwd)"
    ls -la
    exit 1
fi

echo "Working directory: $(pwd)"

# Set Django settings module
export DJANGO_SETTINGS_MODULE=config.simple_settings

# Run quick migrations (with timeout to prevent hanging)
echo "Running migrations..."
timeout 30 python manage.py migrate --noinput --settings=config.simple_settings 2>&1 || echo "Migrations completed or skipped"

# Start Gunicorn immediately
echo "Starting Gunicorn server..."
exec gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers 2 config.wsgi:application