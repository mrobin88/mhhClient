#!/bin/bash
# Azure App Service Startup Script
# This script runs in /home/site/wwwroot

echo "=== Azure App Service Startup ==="
echo "Working directory: $(pwd)"
echo "Python version: $(python --version)"
echo "Python path: $(which python)"

# Try to activate virtual environment (Oryx creates this)
VENV_PATH="/home/site/wwwroot/antenv/bin/activate"
if [ -f "$VENV_PATH" ]; then
    echo "Activating virtual environment at $VENV_PATH"
    source "$VENV_PATH"
    echo "Virtual environment activated"
    echo "Python path after activation: $(which python)"
else
    echo "WARNING: Virtual environment not found at $VENV_PATH"
    echo "Checking for other venv locations..."
    find /home/site/wwwroot -name "activate" -type f 2>/dev/null | head -5
fi

# Change to backend directory
cd /home/site/wwwroot/backend || {
    echo "ERROR: backend directory not found in /home/site/wwwroot"
    echo "Contents of /home/site/wwwroot:"
    ls -la /home/site/wwwroot
    exit 1
}

echo "Changed to backend directory: $(pwd)"

# Check if Django is installed
echo "Checking for Django..."
if ! python -c "import django" 2>/dev/null; then
    echo "ERROR: Django is not installed!"
    echo "Installing requirements from $(pwd)/requirements.txt..."
    
    # Try to install requirements
    if [ -f "requirements.txt" ]; then
        pip install --upgrade pip
        pip install -r requirements.txt
    elif [ -f "/home/site/wwwroot/requirements.txt" ]; then
        echo "Using root requirements.txt"
        pip install --upgrade pip
        pip install -r /home/site/wwwroot/requirements.txt
    else
        echo "ERROR: requirements.txt not found!"
        exit 1
    fi
    
    # Verify Django is now installed
    if ! python -c "import django; print(f'Django {django.__version__} installed successfully')"; then
        echo "ERROR: Failed to install Django!"
        exit 1
    fi
else
    python -c "import django; print(f'Django {django.__version__} is installed')"
fi

# Set Django settings module
export DJANGO_SETTINGS_MODULE=config.settings
echo "DJANGO_SETTINGS_MODULE set to: $DJANGO_SETTINGS_MODULE"

# Run migrations
echo "Running database migrations..."
timeout 60 python manage.py migrate --noinput 2>&1 || {
    echo "WARNING: Migrations may have failed or were skipped"
}

# Verify we can import the WSGI application
echo "Verifying WSGI application..."
python -c "from config.wsgi import application; print('WSGI application imported successfully')" || {
    echo "ERROR: Failed to import WSGI application!"
    exit 1
}

# Start Gunicorn (we're already in backend directory)
echo "Starting Gunicorn server..."
echo "Using Python: $(which python)"
echo "Python version: $(python --version)"
exec python -m gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers 2 config.wsgi:application

