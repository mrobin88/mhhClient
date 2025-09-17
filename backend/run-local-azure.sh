#!/bin/bash

# Run Django locally using Azure production env vars when available
# - Loads ../azure-production.local.env if present, else ../azure-production.env
# - Defaults to using Azure Postgres if DATABASE_PASSWORD looks real
# - Falls back to SQLite if --sqlite is passed or placeholder password detected
# - Flags:
#     --sqlite       Force SQLite (ignore Azure DB vars)
#     --force-azure  Force Azure Postgres (override placeholders)
#     --check        Only print effective DB engine and exit (after pg test if requested)
#     --test-pg      Attempt a direct psycopg2 connection to Postgres (sslmode=require)
#     --port N       Runserver on port N (default 8000)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$SCRIPT_DIR"

cd "$BACKEND_DIR"

USE_SQLITE=0
FORCE_AZURE=0
CHECK_ONLY=0
TEST_PG=0
PORT=8000

for arg in "$@"; do
  case "$arg" in
    --sqlite)
      USE_SQLITE=1
      ;;
    --check)
      CHECK_ONLY=1
      ;;
    --test-pg)
      TEST_PG=1
      ;;
    --force-azure)
      FORCE_AZURE=1
      ;;
    --port)
      shift
      PORT=${1:-8000}
      ;;
    *)
      ;;
  esac
done

# Load Azure env if present (prefer local, which is gitignored)
if [ -f "$PROJECT_ROOT/azure-production.local.env" ]; then
  echo "ℹ️  Loading $PROJECT_ROOT/azure-production.local.env"
  set -a
  # shellcheck disable=SC1090
  source "$PROJECT_ROOT/azure-production.local.env"
  set +a
elif [ -f "$PROJECT_ROOT/azure-production.env" ]; then
  echo "ℹ️  Loading $PROJECT_ROOT/azure-production.env"
  set -a
  # shellcheck disable=SC1090
  source "$PROJECT_ROOT/azure-production.env"
  set +a
else
  echo "⚠️  azure-production.env not found at $PROJECT_ROOT/azure-production.env (continuing)"
fi

is_placeholder() {
  case "$1" in
    your-*) return 0 ;;
    *) return 1 ;;
  esac
}

# Map PG* envs to Django DATABASE_* if present or placeholders should be overridden
if [ -n "${PGHOST:-}" ] && { [ -z "${DATABASE_HOST:-}" ] || is_placeholder "${DATABASE_HOST:-}" || [ "$FORCE_AZURE" -eq 1 ]; }; then export DATABASE_HOST="$PGHOST"; fi
if [ -n "${PGUSER:-}" ] && { [ -z "${DATABASE_USER:-}" ] || is_placeholder "${DATABASE_USER:-}" || [ "$FORCE_AZURE" -eq 1 ]; }; then export DATABASE_USER="$PGUSER"; fi
if [ -n "${PGDATABASE:-}" ] && { [ -z "${DATABASE_NAME:-}" ] || is_placeholder "${DATABASE_NAME:-}" || [ "$FORCE_AZURE" -eq 1 ]; }; then export DATABASE_NAME="$PGDATABASE"; fi
if [ -n "${PGPORT:-}" ] && { [ -z "${DATABASE_PORT:-}" ] || is_placeholder "${DATABASE_PORT:-}" || [ "$FORCE_AZURE" -eq 1 ]; }; then export DATABASE_PORT="$PGPORT"; fi
if [ -n "${PGPASSWORD:-}" ] && { [ -z "${DATABASE_PASSWORD:-}" ] || is_placeholder "${DATABASE_PASSWORD:-}" || [ "$FORCE_AZURE" -eq 1 ]; }; then export DATABASE_PASSWORD="$PGPASSWORD"; fi

# Decide whether to use Azure Postgres or SQLite
if [ "$USE_SQLITE" -eq 0 ]; then
  DB_PASS="${DATABASE_PASSWORD:-}"
  if [ -z "$DB_PASS" ] || is_placeholder "$DB_PASS" ; then
    echo "ℹ️  DATABASE_PASSWORD is empty or placeholder; using SQLite"
    USE_SQLITE=1
  else
    echo "ℹ️  Using Azure Postgres from environment"
  fi
fi

if [ "$USE_SQLITE" -eq 1 ]; then
  # Unset DB envs so simple_settings falls back to SQLite
  unset DATABASE_URL DATABASE_PASSWORD DATABASE_HOST DATABASE_NAME DATABASE_USER DATABASE_PORT
fi

# Local-safe overrides
export DEBUG=True
export DJANGO_SETTINGS_MODULE=config.simple_settings
export ALLOWED_HOSTS=localhost,127.0.0.1

# Activate local venv if present
if [ -f "$PROJECT_ROOT/.venv/bin/activate" ]; then
  # shellcheck disable=SC1090
  source "$PROJECT_ROOT/.venv/bin/activate"
fi

# Print effective DB engine
python - <<'PY'
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', os.getenv('DJANGO_SETTINGS_MODULE','config.simple_settings'))
from django.conf import settings
from django import setup
setup()
print("Effective DB engine:", settings.DATABASES['default']['ENGINE'])
print("DB name:", settings.DATABASES['default'].get('NAME'))
PY

# Optional: direct Postgres connectivity test (run before early exit)
if [ "$TEST_PG" -eq 1 ]; then
  python - <<'PY'
import os, sys
try:
    import psycopg2
    from psycopg2 import OperationalError
except Exception as e:
    print('❌ psycopg2 not installed in this venv. Install with: pip install psycopg2-binary')
    sys.exit(3)

host = os.getenv('DATABASE_HOST') or os.getenv('PGHOST')
user = os.getenv('DATABASE_USER') or os.getenv('PGUSER')
password = os.getenv('DATABASE_PASSWORD') or os.getenv('PGPASSWORD')
dbname = os.getenv('DATABASE_NAME') or os.getenv('PGDATABASE') or 'postgres'
port = int(os.getenv('DATABASE_PORT') or os.getenv('PGPORT') or '5432')

try:
    conn = psycopg2.connect(
        host=host, user=user, password=password, dbname=dbname, port=port,
        sslmode='require', connect_timeout=10
    )
    cur = conn.cursor()
    cur.execute('SELECT version()')
    ver = cur.fetchone()[0]
    print('✅ Connected to Postgres:', ver)
    cur.close(); conn.close()
except OperationalError as e:
    print('❌ Postgres connection failed:', e)
    sys.exit(2)
PY
fi

if [ "$CHECK_ONLY" -eq 1 ]; then
  echo "✅ Check complete."
  exit 0
fi

# Run migrations and start server
python manage.py migrate --settings=config.simple_settings
python manage.py runserver 0.0.0.0:"$PORT" --settings=config.simple_settings
