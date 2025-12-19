#!/bin/bash
# Azure App Service Startup Script for Django
# Fast startup - starts Gunicorn immediately

# Set the working directory
if [ -d "/home/site/wwwroot/backend" ]; then
    cd /home/site/wwwroot/backend
elif [ -d "/home/site/wwwroot" ]; then
    cd /home/site/wwwroot
    if [ ! -f "manage.py" ] && [ -d "backend" ]; then
        cd backend
    fi
fi

# Set Django settings module
export DJANGO_SETTINGS_MODULE=config.simple_settings

# Run quick migrations (with timeout to prevent hanging)
echo "Running migrations..."
timeout 60 python manage.py migrate --noinput --settings=config.simple_settings || echo "Migrations completed or skipped"

# Start Gunicorn immediately (don't wait for collectstatic)
echo "Starting Gunicorn server..."
exec gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers 2 config.wsgi:application