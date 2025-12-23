#!/bin/bash
# Startup script - Activate venv created by Oryx and start Gunicorn
cd /home/site/wwwroot

# Activate the virtual environment created by Oryx
if [ -d "/home/site/wwwroot/antenv" ]; then
    source /home/site/wwwroot/antenv/bin/activate
elif [ -d "/home/site/wwwroot/.venv" ]; then
    source /home/site/wwwroot/.venv/bin/activate
fi

export DJANGO_SETTINGS_MODULE=config.simple_settings

# Use python -m gunicorn to ensure we use the venv's Python
exec python -m gunicorn --bind=0.0.0.0:8000 --timeout 600 config.wsgi:application
