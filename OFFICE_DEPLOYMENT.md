# Office Deployment Guide

## Overview
This guide will help you deploy the MHH Client Management System on your office Linux machine.

## Prerequisites
- Linux machine with Docker and Docker Compose installed
- Network access from your office computers
- Port 5432 available for PostgreSQL

## Step 1: Copy Files to Office Machine
Copy these files to your office Linux machine:
```
docker-compose.yml
init.sql
env.example
deploy.sh
backend/ (entire folder)
```

## Step 2: Run Deployment Script
```bash
# Make script executable (if not already)
chmod +x deploy.sh

# Run deployment
./deploy.sh
```

## Step 3: Configure Environment
Edit the `.env` file created by the script:
```bash
# Replace YOUR_OFFICE_IP with your actual office machine IP
DATABASE_HOST=YOUR_OFFICE_IP
DATABASE_PORT=5432
DATABASE_NAME=mhh_client_db
DATABASE_USER=mhh_user
DATABASE_PASSWORD=mhh_password_2024
```

## Step 4: Setup Django Backend
```bash
cd backend

# Install Python dependencies
pip install -r requirements.txt

# Run database migrations
python manage.py makemigrations
python manage.py migrate

# Create admin user
python manage.py createsuperuser

# Start Django server
python manage.py runserver 0.0.0.0:8000
```

## Step 5: Configure Frontend
Update the frontend API endpoint in `frontend/src/components/ClientForm.vue`:
```javascript
// Change this line:
const response = await axios.post('http://localhost:8000/api/clients/', form.value)

// To your office machine IP:
const response = await axios.post('http://YOUR_OFFICE_IP:8000/api/clients/', form.value)
```

## Step 6: Test the System
1. **Frontend**: Navigate to your frontend URL
2. **Backend**: Navigate to `http://YOUR_OFFICE_IP:8000/admin`
3. **Database**: Verify connection with `docker-compose exec postgres psql -U mhh_user -d mhh_client_db`

## Network Configuration
- **PostgreSQL**: Port 5432 (internal office network only)
- **Django**: Port 8000 (accessible from office computers)
- **Frontend**: Port 5173 (accessible from office computers)

## Security Considerations
- Change default passwords in production
- Restrict database access to office network only
- Use firewall rules to limit external access
- Regular database backups
- Monitor access logs

## Troubleshooting
- **Database connection failed**: Check Docker container status with `docker-compose ps`
- **Port already in use**: Change ports in docker-compose.yml
- **Permission denied**: Ensure proper file permissions and Docker group membership

## Support
For technical issues, check:
1. Docker container logs: `docker-compose logs postgres`
2. Django logs: Check console output
3. Network connectivity: `ping YOUR_OFFICE_IP`

## Backup and Maintenance
```bash
# Database backup
docker-compose exec postgres pg_dump -U mhh_user mhh_client_db > backup.sql

# Restore database
docker-compose exec -T postgres psql -U mhh_user mhh_client_db < backup.sql

# Update system
docker-compose pull postgres
docker-compose up -d postgres
```
