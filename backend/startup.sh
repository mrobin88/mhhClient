#!/bin/bash
# Azure App Service Startup Script with File Structure Logging

echo "=== ROOT DIRECTORY ==="
ls -la /home/site/wwwroot/

echo ""
echo "=== BACKEND DIRECTORY ==="
ls -la /home/site/wwwroot/backend/ 2>&1 || echo "backend/ does not exist"

echo ""
echo "=== CONFIG AT ROOT ==="
ls -la /home/site/wwwroot/config/ 2>&1 || echo "config/ does not exist at root"

echo ""
echo "=== CONFIG IN BACKEND ==="
ls -la /home/site/wwwroot/backend/config/ 2>&1 || echo "backend/config/ does not exist"

echo ""
echo "=== REQUIREMENTS.TXT LOCATIONS ==="
find /home/site/wwwroot -name "requirements.txt" -type f 2>&1

echo ""
echo "=== MANAGE.PY LOCATIONS ==="
find /home/site/wwwroot -name "manage.py" -type f 2>&1

echo ""
echo "=== WSGI.PY LOCATIONS ==="
find /home/site/wwwroot -name "wsgi.py" -type f 2>&1

echo ""
echo "=== ANTENV ==="
ls -la /home/site/wwwroot/antenv/ 2>&1 | head -10 || echo "antenv/ does not exist"

echo ""
echo "=== STARTING APP ==="
cd /home/site/wwwroot/backend || cd /home/site/wwwroot

if [ ! -d "/home/site/wwwroot/antenv" ]; then
    echo "Creating virtual environment..."
    python -m venv /home/site/wwwroot/antenv
    source /home/site/wwwroot/antenv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
else
    echo "Using existing virtual environment..."
    source /home/site/wwwroot/antenv/bin/activate
fi

export DJANGO_SETTINGS_MODULE=config.simple_settings
export PYTHONPATH=/home/site/wwwroot/backend:$PYTHONPATH

cd /home/site/wwwroot/backend || cd /home/site/wwwroot

echo "Current directory: $(pwd)"
echo "Python path: $PYTHONPATH"

exec python -m gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers 2 --pythonpath /home/site/wwwroot/backend config.wsgi:application
