#!/bin/bash

echo "🚀 MHH Client System Deployment Script"
echo "======================================"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

echo "✅ Docker and Docker Compose found"

# Create .env file from example
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp env.example .env
    echo "⚠️  Please edit .env file with your office machine IP address"
else
    echo "✅ .env file already exists"
fi

# Start PostgreSQL database
echo "🐘 Starting PostgreSQL database..."
docker-compose up -d postgres

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
sleep 10

# Check database health
if docker-compose exec postgres pg_isready -U mhh_user -d mhh_client_db; then
    echo "✅ Database is ready!"
else
    echo "❌ Database failed to start properly"
    exit 1
fi

echo ""
echo "🎉 Deployment completed successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Edit .env file with your office machine IP"
echo "2. Copy backend/ folder to your Django server"
echo "3. Run: pip install -r requirements.txt"
echo "4. Run: python manage.py migrate"
echo "5. Run: python manage.py createsuperuser"
echo "6. Run: python manage.py runserver"
echo ""
echo "🌐 Frontend will be available at: http://localhost:5173"
echo "🔧 Admin interface will be available at: http://localhost:8000/admin"
echo ""
echo "📊 Database connection:"
echo "   Host: localhost (or your office IP)"
echo "   Port: 5432"
echo "   Database: mhh_client_db"
echo "   User: mhh_user"
echo "   Password: mhh_password_2024"
