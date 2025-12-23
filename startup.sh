#!/bin/bash
# Azure App Service Startup Script
# This script runs in /home/site/wwwroot

set -e  # Exit on error

echo "=== Azure App Service Startup ==="
echo "Working directory: $(pwd)"
echo "Python version: $(python --version)"

# Change to backend directory
cd backend || {
    echo "ERROR: backend directory not found"
    ls -la
    exit 1
}

# Activate virtual environment if it exists
if [ -f "/home/site/wwwroot/antenv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source /home/site/wwwroot/antenv/bin/activate
else
    echo "WARNING: Virtual environment not found at /home/site/wwwroot/antenv"
fi

# Verify Django is installed
python -c "import django; print(f'Django version: {django.__version__}')" || {
    echo "ERROR: Django is not installed!"
    echo "Installing requirements..."
    pip install -r requirements.txt
}

# Set Django settings module
export DJANGO_SETTINGS_MODULE=config.settings

# Run migrations
echo "Running database migrations..."
timeout 60 python manage.py migrate --noinput 2>&1 || {
    echo "WARNING: Migrations may have failed or were skipped"
}

# Start Gunicorn (we're already in backend directory)
echo "Starting Gunicorn server..."
exec gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers 2 config.wsgi:application

