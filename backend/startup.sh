#!/bin/bash
# Azure App Service Startup Script for Django

set -e  # Exit on any error

# Set the working directory
cd /home/site/wwwroot

echo "Starting Django application setup..."

# Run database migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Setup complete. Starting Gunicorn..."

# Start Gunicorn with exec to replace the shell process
exec gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers 2 config.wsgi:application