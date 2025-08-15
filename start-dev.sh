#!/bin/bash

# Mission Hiring Hall Client System - Development Startup Script
# This script starts both the Django backend and Vue frontend

echo "🚀 Starting Mission Hiring Hall Client System..."
echo "================================================"

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Please run this script from the project root directory"
    exit 1
fi

# Function to cleanup background processes
cleanup() {
    echo "🛑 Shutting down development servers..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit 0
}

# Set up signal handling
trap cleanup SIGINT SIGTERM

# Start Django Backend
echo "🐍 Starting Django Backend..."
cd backend

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install requirements
echo "📥 Installing Python dependencies..."
pip install -r requirements.txt

# Run migrations
echo "🗄️  Running database migrations..."
python manage.py makemigrations
python manage.py migrate

# Create superuser if it doesn't exist
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

# Start Django server in background
echo "🌐 Starting Django server on http://localhost:8000..."
python manage.py runserver 0.0.0.0:8000 &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 3

# Start Vue Frontend
echo "🎨 Starting Vue Frontend..."
cd ../frontend

# Install Node dependencies
echo "📥 Installing Node.js dependencies..."
npm install

# Start Vite dev server in background
echo "⚡ Starting Vite dev server on http://localhost:5173..."
npm run dev &
FRONTEND_PID=$!

# Wait a moment for frontend to start
sleep 3

echo ""
echo "✅ Development servers started successfully!"
echo ""
echo "🌐 Backend API: http://localhost:8000"
echo "   - Admin Panel: http://localhost:8000/admin"
echo "   - API Endpoints: http://localhost:8000/api/"
echo ""
echo "🎨 Frontend App: http://localhost:5173"
echo "   - Client Intake Form"
echo "   - Staff Dashboard"
echo ""
echo "👤 Admin Login:"
echo "   - Username: admin"
echo "   - Password: admin123"
echo ""
echo "📊 Available URLs:"
echo "   - Client Intake: http://localhost:5173/"
echo "   - Staff Dashboard: http://localhost:5173/dashboard"
echo "   - Admin Panel: http://localhost:8000/admin"
echo ""
echo "🛑 Press Ctrl+C to stop all servers"
echo ""

# Wait for user to stop
wait
