#!/bin/bash
# Azure App Service Startup Script for Django

set -e  # Exit on any error

# Set the working directory - try both possible locations
if [ -d "/home/site/wwwroot/backend" ]; then
    cd /home/site/wwwroot/backend
elif [ -d "/home/site/wwwroot" ]; then
    cd /home/site/wwwroot
    # If manage.py is not here, try backend subdirectory
    if [ ! -f "manage.py" ] && [ -d "backend" ]; then
        cd backend
    fi
else
    echo "ERROR: Cannot find working directory"
    exit 1
fi

echo "Starting Django application setup..."
echo "Working directory: $(pwd)"

# Set Django settings module
export DJANGO_SETTINGS_MODULE=config.simple_settings

# Run database migrations (with error handling)
echo "Running database migrations..."
python manage.py migrate --noinput --settings=config.simple_settings || {
    echo "WARNING: Migration failed, continuing anyway..."
}

# Collect static files (with error handling)
echo "Collecting static files..."
python manage.py collectstatic --noinput --settings=config.simple_settings || {
    echo "WARNING: Static file collection failed, continuing anyway..."
}

echo "Setup complete. Starting Gunicorn..."

# Start Gunicorn with exec to replace the shell process
exec gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers 2 config.wsgi:application