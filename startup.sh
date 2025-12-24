#!/bin/bash
# Startup script for Azure App Service
# Django is at root, WSGI is at config.wsgi:application

cd /home/site/wwwroot

# Activate the virtual environment created by Oryx
if [ -d "/home/site/wwwroot/antenv" ]; then
    source /home/site/wwwroot/antenv/bin/activate
elif [ -d "/home/site/wwwroot/.venv" ]; then
    source /home/site/wwwroot/.venv/bin/activate
fi

export DJANGO_SETTINGS_MODULE=config.simple_settings

# Start Gunicorn with correct WSGI path (config.wsgi:application)
exec gunicorn --bind=0.0.0.0:8000 --timeout 600 config.wsgi:application
