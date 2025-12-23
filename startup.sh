#!/bin/bash
# Azure App Service Startup Script
# This script runs in /home/site/wwwroot

echo "=== Azure App Service Startup - Diagnostic ==="
echo "Current working directory: $(pwd)"
echo "Python version: $(python --version)"
echo "Python path: $(which python)"

# Show the actual file structure
echo ""
echo "=== File Structure Analysis ==="
echo "Contents of /home/site/wwwroot:"
ls -la /home/site/wwwroot | head -20

echo ""
echo "Checking for backend folder:"
if [ -d "/home/site/wwwroot/backend" ]; then
    echo "✅ backend folder exists"
    echo "Contents of backend:"
    ls -la /home/site/wwwroot/backend | head -10
else
    echo "❌ backend folder NOT found"
fi

echo ""
echo "Checking for config folder locations:"
if [ -d "/home/site/wwwroot/config" ]; then
    echo "✅ config folder at ROOT: /home/site/wwwroot/config"
    ls -la /home/site/wwwroot/config | head -5
fi
if [ -d "/home/site/wwwroot/backend/config" ]; then
    echo "✅ config folder in backend: /home/site/wwwroot/backend/config"
    ls -la /home/site/wwwroot/backend/config | head -5
fi

echo ""
echo "Checking for manage.py locations:"
find /home/site/wwwroot -name "manage.py" -type f 2>/dev/null

echo ""
echo "Checking for requirements.txt locations:"
find /home/site/wwwroot -name "requirements.txt" -type f 2>/dev/null

echo ""
echo "Checking for virtual environment:"
find /home/site/wwwroot -name "antenv" -type d 2>/dev/null
if [ -f "/home/site/wwwroot/antenv/bin/activate" ]; then
    echo "✅ Found venv at /home/site/wwwroot/antenv"
    source /home/site/wwwroot/antenv/bin/activate
    echo "Virtual environment activated"
    echo "Python path after activation: $(which python)"
else
    echo "❌ Virtual environment not found at /home/site/wwwroot/antenv"
fi

# Determine the correct working directory
echo ""
echo "=== Determining Working Directory ==="
if [ -f "/home/site/wwwroot/manage.py" ]; then
    echo "✅ manage.py found at ROOT - working from root"
    WORK_DIR="/home/site/wwwroot"
elif [ -f "/home/site/wwwroot/backend/manage.py" ]; then
    echo "✅ manage.py found in backend/ - working from backend"
    WORK_DIR="/home/site/wwwroot/backend"
else
    echo "❌ ERROR: manage.py not found!"
    exit 1
fi

cd "$WORK_DIR"
echo "Changed to: $(pwd)"

# Check if Django is installed
echo ""
echo "=== Checking Django Installation ==="
if ! python -c "import django" 2>/dev/null; then
    echo "❌ Django is not installed!"
    echo "Installing requirements..."
    
    if [ -f "requirements.txt" ]; then
        pip install --upgrade pip
        pip install -r requirements.txt
    elif [ -f "/home/site/wwwroot/requirements.txt" ]; then
        pip install --upgrade pip
        pip install -r /home/site/wwwroot/requirements.txt
    else
        echo "❌ ERROR: requirements.txt not found!"
        exit 1
    fi
    
    # Verify Django is now installed
    if ! python -c "import django; print(f'✅ Django {django.__version__} installed')"; then
        echo "❌ ERROR: Failed to install Django!"
        exit 1
    fi
else
    python -c "import django; print(f'✅ Django {django.__version__} is installed')"
fi

# Set Django settings module
export DJANGO_SETTINGS_MODULE=config.settings
echo "DJANGO_SETTINGS_MODULE set to: $DJANGO_SETTINGS_MODULE"

# Run migrations
echo ""
echo "=== Running Migrations ==="
timeout 60 python manage.py migrate --noinput 2>&1 || {
    echo "⚠️  WARNING: Migrations may have failed or were skipped"
}

# Verify we can import the WSGI application
echo ""
echo "=== Verifying WSGI Application ==="
python -c "from config.wsgi import application; print('✅ WSGI application imported successfully')" || {
    echo "❌ ERROR: Failed to import WSGI application!"
    echo "Python path:"
    python -c "import sys; print('\n'.join(sys.path))"
    exit 1
}

# Start Gunicorn
echo ""
echo "=== Starting Gunicorn ==="
echo "Working directory: $(pwd)"
echo "Using Python: $(which python)"
echo "Python version: $(python --version)"
exec python -m gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers 2 config.wsgi:application
