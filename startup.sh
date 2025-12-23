#!/bin/bash
# Simple startup - Azure handles venv and dependencies via Oryx build
cd /home/site/wwwroot
export DJANGO_SETTINGS_MODULE=config.simple_settings
exec gunicorn --bind=0.0.0.0:8000 --timeout 600 config.wsgi:application
