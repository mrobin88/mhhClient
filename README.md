# 🎯 Client Services Management System

**Production-ready client intake and case management system for service organizations.**

## 🌟 **Live System**
- **Frontend**: https://blue-glacier-0c5f06410.3.azurestaticapps.net/
- **Backend API**: https://mhh-client-backend-cuambzgeg3dfbphd.centralus-01.azurewebsites.net/api/
- **Admin Interface**: https://mhh-client-backend-cuambzgeg3dfbphd.centralus-01.azurewebsites.net/admin/

## ✨ **Features**
- **Client Intake System** - Streamlined online registration with resume upload
- **Case Notes Management** - Timestamped case notes with visual follow-up indicators
- **Email Notifications** - Automated follow-up reminders for case notes
- **CSV Export** - Export case notes and client data for reporting
- **Staff Dashboard** - Search, manage, and monitor client caseloads
- **Admin Interface** - Complete system administration with Django admin
- **Document Management** - Secure file uploads and storage via Azure Blob Storage

## 🛠️ **Production Stack**
- **Frontend**: Vue.js 3 + TypeScript + Tailwind CSS → Azure Static Web Apps
- **Backend**: Django 5.1.15 + Django REST Framework → Azure App Service
- **Database**: PostgreSQL → Azure Database for PostgreSQL
- **Storage**: Azure Blob Storage (for documents/resumes)
- **Deployment**: GitHub Actions → Auto-deploy on push to main
- **Server**: Gunicorn with WhiteNoise for static files

## 🚀 **Local Development**

```bash
# Start development servers
./start-dev.sh

# Access local system
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000/api/
# Admin: http://localhost:8000/admin/
```

### Environment Setup

1. Copy `env.example` to `.env` and configure:
   ```bash
   cp env.example .env
   # Edit .env with your database credentials
   ```

2. For frontend, copy `frontend/env.production.template` to `frontend/.env.local`:
   ```bash
   cp frontend/env.production.template frontend/.env.local
   # Update VITE_API_URL if needed
   ```

3. Install dependencies:
   ```bash
   # Backend
   pip install -r requirements.txt
   
   # Frontend
   cd frontend && npm install
   ```

4. Run migrations:
   ```bash
   python manage.py migrate
   ```

5. Create superuser:
   ```bash
   python manage.py createsuperuser
   ```

## 📚 **Documentation**
- **Case Notes Guide**: [CASE_NOTES_GUIDE.md](CASE_NOTES_GUIDE.md) - How to use the case notes system
- **Project Specs**: [MISSION_HIRING_HALL_SPECS.md](MISSION_HIRING_HALL_SPECS.md) - Complete project specifications

## 🔧 **Project Structure**

```
mhhClient/
├── config/              # Django settings (simple_settings.py)
├── clients/             # Client management app
├── users/               # User/staff management app
├── frontend/            # Vue.js frontend
├── static/              # Static files (CSS, JS)
├── media/               # Media uploads (local dev only)
├── manage.py           # Django management script
├── requirements.txt    # Python dependencies
├── runtime.txt         # Python version (3.11)
└── startup.sh          # Azure startup script
```

## 📝 **Key Configuration**

- **Settings**: `config/simple_settings.py` (used in production and development)
- **Database**: Configured via environment variables (see `env.example`)
- **Static Files**: Served via WhiteNoise in production
- **Media Files**: Stored in Azure Blob Storage in production

## 🔐 **Security Notes**

- All secrets are managed via environment variables
- Never commit `.env` files or files containing secrets
- Production secrets are configured in Azure App Service settings
- Django 5.1.15 includes critical SQL injection security fixes

---

**Professional client services management platform** 🏗️
