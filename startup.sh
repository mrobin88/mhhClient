#!/bin/bash
# Optimized startup script for Azure App Service - Django backend
# Fixes: Removes aggressive venv check that causes corruption loops

set -e
cd /home/site/wwwroot

echo "=== Starting Django Application Startup ==="
echo "Time: $(date)"

VENV_DIR="antenv"
VENV_BIN="$VENV_DIR/bin"
PYTHON="$VENV_BIN/python"
PIP="$VENV_BIN/pip"

# ============================================================================
# VENV MANAGEMENT - Create only if missing (NO corruption checks)
# ============================================================================

if [ ! -d "$VENV_BIN" ]; then
    echo "Virtual environment not found. Creating..."
    python3.11 -m venv "$VENV_DIR"
    echo "✓ Virtual environment created."
fi

# ============================================================================
# DEPENDENCY INSTALLATION - Smart caching with marker file
# ============================================================================

MARKER_FILE="$VENV_DIR/.requirements_installed"

if [ ! -f "$MARKER_FILE" ] || [ requirements.txt -nt "$MARKER_FILE" ]; then
    echo "Installing/updating dependencies..."
    
    # Activate venv for pip operations
    source "$VENV_BIN/activate"
    
    # Upgrade pip first
    pip install --upgrade pip setuptools wheel --quiet 2>&1 | grep -v "already satisfied" || true
    
    # Install requirements
    pip install \
        --no-cache-dir \
        --disable-pip-version-check \
        -r requirements.txt
    
    deactivate
    touch "$MARKER_FILE"
    echo "✓ Dependencies installed successfully."
else
    echo "✓ Dependencies up-to-date (using cache)."
fi

# ============================================================================
# QUICK VERIFICATION
# ============================================================================

echo "Verifying Django installation..."
source "$VENV_BIN/activate"

if ! $PYTHON -c "import django; print(f'Django {django.get_version()}')" 2>/dev/null; then
    echo "✗ FATAL: Django not installed!"
    exit 1
fi

echo "✓ Django verified."

# ============================================================================
# DJANGO SETUP
# ============================================================================

export DJANGO_SETTINGS_MODULE=config.simple_settings
export PYTHONPATH=/home/site/wwwroot:$PYTHONPATH
export PYTHONUNBUFFERED=1

echo "Django settings: $DJANGO_SETTINGS_MODULE"

# Run migrations (non-blocking)
echo "Running database migrations..."
if $PYTHON manage.py migrate --noinput 2>&1 | tail -5; then
    echo "✓ Migrations completed."
else
    echo "⚠ Migration skipped (database may not be configured yet)."
fi

# Collect static files (non-blocking)
echo "Collecting static files..."
if $PYTHON manage.py collectstatic --noinput --clear 2>&1 | tail -3; then
    echo "✓ Static files collected."
else
    echo "⚠ Collectstatic skipped."
fi

# ============================================================================
# START APPLICATION
# ============================================================================

echo ""
echo "=== Starting Gunicorn on port 8000 ==="
echo ""

WORKERS=$(($(nproc) * 2 + 1))
[ $WORKERS -gt 8 ] && WORKERS=8

exec $PYTHON -m gunicorn \
    --bind 0.0.0.0:8000 \
    --workers $WORKERS \
    --worker-class sync \
    --worker-connections 1000 \
    --timeout 120 \
    --keepalive 5 \
    --max-requests 1000 \
    --access-logformat '%({X-Forwarded-For}i)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s' \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    config.wsgi:application