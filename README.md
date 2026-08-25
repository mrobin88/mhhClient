# Client Services Management System

Internal staff app for intake, case notes, classes, documents, and reports.

Staff-facing help is the **Guide** screen in the signed-in staff app. Setup notes below are for sitting down with the code in person.

## Stack

- Frontend: Vue 3 + TypeScript + Tailwind
- Backend: Django + Django REST Framework
- Storage: Azure Blob Storage
- Hosting: Azure Static Web Apps + Azure App Service

## Local setup

```bash
cp env.example .env
python3 -m venv venv
venv/bin/pip install -r requirements.txt
npm --prefix frontend install
venv/bin/python manage.py migrate
venv/bin/python manage.py createsuperuser
./start-dev.sh
```

- Staff app: `http://localhost:5173/staff/`
- Django: `http://localhost:8000/admin/`
- Public frontend: `http://localhost:5173`
