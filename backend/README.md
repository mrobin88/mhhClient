# 🎯 Django Backend - Mission Hiring Hall

**Production Django API backend for client management system.**

## 🌟 **Production URLs**
- **API**: https://mhh-client-backend-cuambzgeg3dfbphd.centralus-01.azurewebsites.net/api/
- **Admin**: https://mhh-client-backend-cuambzgeg3dfbphd.centralus-01.azurewebsites.net/admin/

## 🚀 **Local Development**

```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate --settings=config.simple_settings

# Create superuser
python manage.py createsuperuser --settings=config.simple_settings

# Start development server
python manage.py runserver --settings=config.simple_settings
```

## 🔧 **Configuration**

### **Settings Files**
- `config/simple_settings.py` - Development (SQLite)
- `config/production_settings.py` - Production (PostgreSQL)

### **Environment Variables**
- `SECRET_KEY` - Django secret key
- `DEBUG` - Debug mode
- `DATABASE_PASSWORD` - PostgreSQL password
- `CORS_ALLOWED_ORIGINS` - Frontend URLs

## 🧪 **Testing**

```bash
# Run integration tests
python test_integration.py

# Run production deployment check
python deploy_production.py
```

## 📊 **API Endpoints**
- `GET/POST /api/clients/` - Client management
- `GET /api/clients/?search=query` - Client search
- `GET/POST /api/case-notes/` - Case notes
- `GET /api/clients/{id}/case-notes/` - Client case notes
- `/admin/` - Django admin interface# Trigger deployment - Wed Sep 17 15:40:10 PDT 2025
