# Client Services Management System

Internal client intake and case-management platform for staff and managers.

## What It Does

- Client intake + profile management
- Case notes + follow-up tracking
- Staff/admin workflows for updates and oversight
- CSV reporting exports
- Document upload and storage
- Staff-managed classes/JRT sessions and attendance
- Expiring, document-scoped upload links for client outreach

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

## Local Setup

Prerequisites: Python 3.11, Node.js 18+, and npm. PostgreSQL and Azure services are
optional for local development; without database credentials Django uses local SQLite.

```bash
cp env.example .env
python3 -m venv venv
venv/bin/pip install -r requirements.txt
npm --prefix frontend install
venv/bin/python manage.py migrate
venv/bin/python manage.py createsuperuser
./start-dev.sh
```

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000/api/`
- Admin: `http://localhost:8000/admin/`
- Staff app: `http://localhost:5173/staff/`

Do not copy `frontend/env.production.template` for local development. Vite proxies
`/api` to `http://localhost:8000` when no frontend API URL is set.

### Database choices

- **SQLite:** leave `DATABASE_PASSWORD` and `DATABASE_URL` unset. This is the easiest
  option for frontend work and most tests.
- **PostgreSQL:** set the `DATABASE_*` variables in `.env`.

### Sensitive-field encryption

SSNs use application-level Fernet encryption. Generate a development-only key:

```bash
venv/bin/python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Then set `SSN_ENCRYPTION_KEYS=v1:<generated-key>` and
`SSN_ACTIVE_KEY_ID=v1` in `.env`. Never reuse a development key in production.

### Checks

```bash
venv/bin/python manage.py test
venv/bin/python manage.py check
npm --prefix frontend run build
venv/bin/python manage.py makemigrations --check --dry-run
```

## Workflow overview

1. A person registers publicly, checks in at the kiosk, arrives through a partner
   referral, or is entered by staff from an outside interest form.
2. Staff maintain the client profile, case notes, program stage, classes/JRTs, and
   documents in the authenticated staff app.
3. Staff can send an expiring upload link scoped to specific missing documents.
   Public upload links cannot read or download client records.
4. Managers use authenticated reports and exports for operations and audits.

Production URLs, credentials, client data, and internal support contacts do not belong
in this public repository.

## Docs

- **How everything works** — the maintained guide for staff and admins lives in the staff app at
  `/staff/#/how-it-works` ([StaffHowItWorks.vue](frontend/src/staff/components/StaffHowItWorks.vue)).
  Update that page rather than adding new markdown files.
- Staff links and quick fixes: `STAFF_GUIDE.md`
- Partner referral ingest API: `/partners/` ([PartnersApp.vue](frontend/src/partners/PartnersApp.vue))
- Worker portal (clock in/out, incident reports): `/worker/` ([WorkerApp.vue](frontend/src/worker/WorkerApp.vue))
- Client check-in kiosk: `/checkin` ([CheckInApp.vue](frontend/src/checkin/CheckInApp.vue))
