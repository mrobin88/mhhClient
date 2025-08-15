# MHH Client Management System

A Django-based client management system with Vue.js frontend for nonprofit organizations.

## Features

- **Client Intake**: Comprehensive client information collection form
- **Staff Authentication**: Role-based access control for staff members
- **Admin Interface**: Django admin for data management and reporting
- **PostgreSQL Database**: Robust data storage with Docker deployment

## Quick Start

### 1. Frontend (Client Intake)
```bash
cd frontend
npm install
npm run dev
```
The frontend will run on `http://localhost:5173`

### 2. Database Setup (Office Machine)
```bash
# Copy these files to your Linux office machine
docker-compose up -d postgres
```

### 3. Backend (Staff Access)
```bash
cd backend
# Copy env.example to .env and update database settings
cp env.example .env

# Install Python dependencies
pip install -r requirements.txt

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run server
python manage.py runserver
```

## Office Deployment

### Database Configuration
- **Host**: Your office machine IP address
- **Port**: 5432 (PostgreSQL default)
- **Database**: mhh_client_db
- **User**: mhh_user
- **Password**: mhh_password_2024

### Environment Variables
Copy `env.example` to `.env` and update:
```bash
DATABASE_HOST=YOUR_OFFICE_MACHINE_IP
DATABASE_PORT=5432
DATABASE_NAME=mhh_client_db
DATABASE_USER=mhh_user
DATABASE_PASSWORD=mhh_password_2024
```

### Staff Roles
- **Administrator**: Full system access
- **Case Manager**: Client management and reporting
- **Counselor**: Client data access
- **Volunteer**: Limited client data access

## Security Notes
- Change default passwords in production
- Use HTTPS in production
- Restrict database access to office network
- Regular database backups recommended

## API Endpoints
- `POST /api/clients/` - Create new client
- `GET /api/clients/` - List clients (staff only)
- `GET /api/clients/{id}/` - Get client details (staff only)

## Support
For technical support, contact your system administrator.

