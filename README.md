# Client Services Management System

Internal client intake and case-management platform for staff and managers.

## What It Does

- Client intake + profile management
- Case notes + follow-up tracking
- Staff/admin workflows for updates and oversight
- CSV reporting exports
- Document upload and storage

## End-User Flow

1. Client submits intake form.
2. Staff review/update client profile.
3. Staff log case notes and follow-up dates.
4. Managers export reports for operations/audits.

## Stack

- Frontend: Vue 3 + TypeScript + Tailwind
- Backend: Django + Django REST Framework
- Database: PostgreSQL
- Storage: Azure Blob Storage
- Hosting: Azure Static Web Apps + Azure App Service
- Server: Gunicorn + WhiteNoise

## Hosting and CI/CD

- Production is hosted on Azure services.
- Deployments run via GitHub Actions on push/merge to `main`.
- Runtime config and secrets are environment-variable based.

## Development Notes

Built and maintained end-to-end by one developer (product design, implementation, cloud hosting, CI/CD, and support) with an iterative, pragmatic shipping style.

## Local Setup

```bash
cp env.example .env
cp frontend/env.production.template frontend/.env.local
pip install -r requirements.txt
cd frontend && npm install && cd ..
python manage.py migrate
./start-dev.sh
```

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000/api/`
- Admin: `http://localhost:8000/admin/`

## Docs

- **How everything works** — the maintained guide for staff and admins lives in the staff app at
  `/staff/#/how-it-works` ([StaffHowItWorks.vue](frontend/src/staff/components/StaffHowItWorks.vue)).
  Update that page rather than adding new markdown files.
- Staff links and quick fixes: `STAFF_GUIDE.md`
- Partner referral ingest API: `/partners/` ([PartnersApp.vue](frontend/src/partners/PartnersApp.vue))
