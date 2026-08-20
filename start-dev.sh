#!/bin/bash
set -euo pipefail

if [ ! -f "manage.py" ] || [ ! -d "frontend" ]; then
    echo "Run this script from the repository root."
    exit 1
fi

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

"venv/bin/pip" install -r requirements.txt
npm --prefix frontend install
"venv/bin/python" manage.py migrate

cleanup() {
    kill "${BACKEND_PID:-}" "${FRONTEND_PID:-}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

"venv/bin/python" manage.py runserver 127.0.0.1:8000 &
BACKEND_PID=$!
npm --prefix frontend run dev -- --host 127.0.0.1 &
FRONTEND_PID=$!

echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:5173"
echo "Create a local login separately with: venv/bin/python manage.py createsuperuser"
echo "Press Ctrl+C to stop both servers."
wait
