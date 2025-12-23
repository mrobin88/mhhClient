#!/bin/bash

# Mission Hiring Hall Client System - Development Startup Script

echo "🚀 Starting Mission Hiring Hall Client System..."

if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Please run this script from the project root directory"
    exit 1
fi

cleanup() {
    echo "🛑 Shutting down development servers..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start Django Backend
echo "🐍 Starting Django Backend..."

if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt

echo "🗄️  Running database migrations..."
python manage.py makemigrations
python manage.py migrate

echo "👤 Checking for superuser..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@mhh.com', 'admin123')
    print('Superuser created: admin/admin123')
else:
    print('Superuser already exists')
"

echo "🌐 Starting Django server on http://localhost:8000..."
python manage.py runserver 0.0.0.0:8000 &
BACKEND_PID=$!

sleep 3

# Start Vue Frontend
echo "🎨 Starting Vue Frontend..."
cd ../frontend

echo "📥 Installing Node.js dependencies..."
npm install

echo "⚡ Starting Vite dev server on http://localhost:5173..."
npm run dev &
FRONTEND_PID=$!

sleep 3

echo ""
echo "✅ Development servers started successfully!"
echo ""
echo "🌐 Backend API: http://localhost:8000"
echo "   - Admin Panel: http://localhost:8000/admin"
echo "   - API Endpoints: http://localhost:8000/api/"
echo ""
echo "🎨 Frontend App: http://localhost:5173"
echo ""
echo "👤 Admin Login: admin/admin123"
echo ""
echo "🛑 Press Ctrl+C to stop all servers"
echo ""

wait
