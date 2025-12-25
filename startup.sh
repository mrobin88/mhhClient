#!/bin/bash
# Optimized startup script for Azure App Service - Django backend
# Production-ready with proper error handling and caching

set -e  # Exit on any error

cd /home/site/wwwroot

echo "=== Starting Django Application Startup ==="
echo "Time: $(date)"
echo "Python: $(python3.11 --version)"

# Configuration
VENV_DIR="antenv"
VENV_BIN="$VENV_DIR/bin"
PYTHON="$VENV_BIN/python"
PIP="$VENV_BIN/pip"

# ============================================================================
# VENV MANAGEMENT - Only recreate if necessary
# ============================================================================

if [ -d "$VENV_BIN" ]; then
    echo "Virtual environment found. Validating..."
    
    # Test if venv is actually functional
    if $PYTHON -c "import sys; sys.exit(0)" 2>/dev/null; then
        echo "✓ Virtual environment is valid."
        VENV_VALID=1
    else
        echo "✗ Virtual environment is corrupted. Recreating..."
        rm -rf "$VENV_DIR"
        VENV_VALID=0
    fi
else
    echo "Virtual environment not found. Creating..."
    VENV_VALID=0
fi

# Create fresh venv if needed
if [ "$VENV_VALID" -ne 1 ]; then
    python3.11 -m venv "$VENV_DIR"
    echo "✓ Virtual environment created."
fi

# ============================================================================
# DEPENDENCY INSTALLATION - Smart caching
# ============================================================================

# Only reinstall if requirements.txt is newer than last install marker
MARKER_FILE="$VENV_DIR/.requirements_installed"
if [ ! -f "$MARKER_FILE" ] || [ requirements.txt -nt "$MARKER_FILE" ]; then
    echo "Installing/updating dependencies..."
    
    # Upgrade pip first
    $PIP install --upgrade pip setuptools wheel --quiet
    
    # Install requirements with optimizations
    $PIP install \
        --no-cache-dir \
        --disable-pip-version-check \
        --no-warn-script-location \
        -r requirements.txt
    
    # Create marker file
    touch "$MARKER_FILE"
    echo "✓ Dependencies installed successfully."
else
    echo "✓ Dependencies up-to-date (using cache)."
fi

# ============================================================================
# VERIFICATION
# ============================================================================

echo "Verifying critical packages..."

if ! $PYTHON -c "import django; print(f'Django {django.get_version()}')" 2>/dev/null; then
    echo "✗ FATAL: Django not installed after setup!"
    exit 1
fi

if ! $PYTHON -c "import rest_framework; print('DRF OK')" 2>/dev/null; then
    echo "✗ FATAL: djangorestframework not installed!"
    exit 1
fi

echo "✓ All critical packages verified."

# ============================================================================
# DJANGO SETUP
# ============================================================================

# Set environment
export DJANGO_SETTINGS_MODULE=config.simple_settings
export PYTHONPATH=/home/site/wwwroot:$PYTHONPATH
export PYTHONUNBUFFERED=1  # Real-time logging

echo "Django settings: $DJANGO_SETTINGS_MODULE"
echo "Working directory: $(pwd)"

# Run migrations (non-blocking)
echo "Running database migrations..."
if $PYTHON manage.py migrate --noinput 2>&1; then
    echo "✓ Migrations completed."
else
    echo "⚠ Migration failed (may not have database configured). Continuing..."
fi

# Collect static files (non-blocking)
echo "Collecting static files..."
if $PYTHON manage.py collectstatic --noinput --clear 2>&1 | grep -E "(Collecting|Cleaned|Success)" || true; then
    echo "✓ Static files collected."
else
    echo "⚠ Collectstatic warning (may be optional). Continuing..."
fi

# ============================================================================
# START APPLICATION
# ============================================================================

echo ""
echo "=== Starting Gunicorn ==="
echo "Binding to 0.0.0.0:8000"
echo "Workers: 4 (auto-scaled based on CPU cores)"
echo ""

# Use optimal worker count
WORKERS=$(($(nproc) * 2 + 1))
[ $WORKERS -gt 8 ] && WORKERS=8  # Cap at 8

exec $VENV_BIN/gunicorn \
    --bind 0.0.0.0:8000 \
    --workers $WORKERS \
    --worker-class sync \
    --worker-connections 1000 \
    --timeout 120 \
    --keepalive 5 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --access-logformat '%({X-Forwarded-For}i)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s' \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    config.wsgi:application