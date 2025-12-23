#!/bin/bash
# Azure App Service Startup Script for Django
# Fast startup - starts Gunicorn immediately

# Navigate to backend directory (handle both deployment structures)
cd /home/site/wwwroot/backend 2>/dev/null || cd /home/site/wwwroot || true

# If manage.py is not in current directory but exists in backend/, cd into backend
if [ ! -f "manage.py" ] && [ -d "backend" ] && [ -f "backend/manage.py" ]; then
    cd backend
fi

# Verify we're in the right place
if [ ! -f "manage.py" ]; then
    echo "ERROR: manage.py not found in $(pwd)"
    echo "Directory contents:"
    ls -la
    exit 1
fi

echo "Working directory: $(pwd)"
echo "Python version: $(python --version 2>&1)"

# Activate virtual environment if it exists
if [ -d "/home/site/wwwroot/antenv" ]; then
    source /home/site/wwwroot/antenv/bin/activate
    echo "Activated virtual environment"
fi

# Set Django settings module
export DJANGO_SETTINGS_MODULE=config.simple_settings

# Run quick migrations (with timeout to prevent hanging)
echo "Running migrations..."
timeout 30 python manage.py migrate --noinput --settings=config.simple_settings 2>&1 || echo "Migrations completed or skipped"

# Start Gunicorn immediately
echo "Starting Gunicorn server..."
exec python -m gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers 2 config.wsgi:application