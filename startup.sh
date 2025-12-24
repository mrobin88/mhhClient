#!/bin/bash
# Startup script for Azure App Service
# Django is at root, WSGI is at config.wsgi:application

cd /home/site/wwwroot

# Create and activate virtual environment if Oryx didn't build it
if [ ! -d "/home/site/wwwroot/antenv" ] && [ ! -d "/home/site/wwwroot/.venv" ]; then
    echo "Creating virtual environment..."
    python3.11 -m venv antenv
    source /home/site/wwwroot/antenv/bin/activate
    echo "Installing dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
elif [ -d "/home/site/wwwroot/antenv" ]; then
    source /home/site/wwwroot/antenv/bin/activate
elif [ -d "/home/site/wwwroot/.venv" ]; then
    source /home/site/wwwroot/.venv/bin/activate
fi

# Set Django settings
export DJANGO_SETTINGS_MODULE=config.simple_settings

# Ensure we're in the right directory and Python can find modules
export PYTHONPATH=/home/site/wwwroot:$PYTHONPATH

# Run migrations
python manage.py migrate --noinput || true

# Start Gunicorn with correct WSGI path (config.wsgi:application)
exec gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers 2 config.wsgi:application
