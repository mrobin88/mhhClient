#!/bin/bash
# Startup script for Azure App Service - Django backend
# Deletes corrupted venv and ensures clean installation

cd /home/site/wwwroot

echo "=== Starting Django Application Startup ==="

# Check if venv exists and is valid BEFORE using it
if [ -d "antenv/bin" ]; then
    echo "Virtual environment found, checking integrity..."
    
    # Try to activate and test Django
    source antenv/bin/activate
    
    # Check if Django is properly installed (critical check)
    if ! python -c "import django.utils" 2>/dev/null; then
        echo "ERROR: Virtual environment is CORRUPTED. Deleting and recreating..."
        deactivate 2>/dev/null || true
        rm -rf antenv
        echo "Corrupted venv deleted. Creating fresh virtual environment..."
        python3.11 -m venv antenv
        source antenv/bin/activate
        echo "Upgrading pip..."
        pip install --upgrade pip --quiet
        echo "Installing dependencies from requirements.txt..."
        pip install -r requirements.txt --no-cache-dir
        echo "Dependencies installed successfully."
    else
        echo "Virtual environment is valid."
    fi
else
    echo "Virtual environment not found. Creating new one..."
    python3.11 -m venv antenv
    source antenv/bin/activate
    echo "Upgrading pip..."
    pip install --upgrade pip --quiet
    echo "Installing dependencies from requirements.txt..."
    pip install -r requirements.txt --no-cache-dir
    echo "Dependencies installed successfully."
fi

# Verify Django installation one more time
if ! python -c "import django" 2>/dev/null; then
    echo "FATAL ERROR: Django still not installed after setup!"
    exit 1
fi

# Set Django settings module
export DJANGO_SETTINGS_MODULE=config.simple_settings
export PYTHONPATH=/home/site/wwwroot:$PYTHONPATH

# Display Python and Django info for debugging
echo "Python version: $(python --version)"
echo "Django version: $(python -c 'import django; print(django.get_version())')"
echo "Django settings: $DJANGO_SETTINGS_MODULE"
echo "Working directory: $(pwd)"

# Run database migrations
echo "Running database migrations..."
python manage.py migrate --noinput || echo "WARNING: Migration failed or skipped"

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput || echo "WARNING: Collectstatic failed or skipped"

# Start Gunicorn with the correct WSGI application
echo "Starting Gunicorn server..."
exec gunicorn \
    --bind=0.0.0.0:8000 \
    --timeout 600 \
    --workers 2 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    config.wsgi:application
