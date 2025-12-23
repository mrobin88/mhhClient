#!/bin/bash
# Azure App Service Startup Script
# Django is deployed at ROOT, not in backend/

cd /home/site/wwwroot

echo "=== Current directory: $(pwd) ==="
echo "=== Files in root ==="
ls -la | head -20

if [ ! -d "/home/site/wwwroot/antenv" ]; then
    echo "Creating virtual environment and installing dependencies..."
    python -m venv /home/site/wwwroot/antenv
    source /home/site/wwwroot/antenv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
else
    echo "Using existing virtual environment..."
    source /home/site/wwwroot/antenv/bin/activate
fi

export DJANGO_SETTINGS_MODULE=config.simple_settings

echo "Starting Gunicorn from $(pwd)"
exec python -m gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers 2 config.wsgi:application
