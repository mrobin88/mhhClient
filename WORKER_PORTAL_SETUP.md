# 🚀 Worker Portal - Quick Setup Guide

## Prerequisites

- Backend is running (Django + PostgreSQL)
- You have access to Django Admin
- Frontend development environment is set up

---

## Step-by-Step Setup

### 1. Apply Migrations (Already Done)

```bash
cd /Users/matthewrobin/Projects/mhhClient
source venv/bin/activate
python manage.py migrate
```

You should see:
```
Applying clients.0011_add_worker_portal_models... OK
```

### 2. Create Your First Worker Account

**Option A: Using Management Command (Easiest)**

```bash
# Create account for existing client
python manage.py create_worker_account "415-555-1234" --approve

# This will:
# - Find client with that phone number
# - Create worker account
# - Set PIN to last 4 digits of phone (5678 in this case)
# - Approve the account immediately
```

**Option B: Using Django Admin**

1. Login to Django Admin: http://localhost:8000/admin/
2. Navigate to "Clients" → "Worker Accounts"
3. Click "Add Worker Account"
4. Fill in:
   - Client: Select a client from dropdown
   - Phone: Enter phone number (must match client)
   - Is Active: ✅ Checked
   - Is Approved: ✅ Checked
   - Created By: Your name
5. Click "Save"
6. PIN will automatically be set to last 4 digits of phone

**Option C: Using Django Shell**

```python
python manage.py shell

from clients.models import Client
from clients.models_extensions import WorkerAccount

# Get a client
client = Client.objects.get(phone='415-555-1234')

# Create worker account
account = WorkerAccount.objects.create(
    client=client,
    phone=client.phone,
    is_active=True,
    is_approved=True,
    created_by='Admin Setup'
)

# Set PIN
account.set_pin('1234')  # Or use phone[-4:]
account.save()

print(f"Created account for {client.full_name}")
exit()
```

### 3. Run the Frontend Development Server

```bash
cd frontend
npm install  # If not already installed
npm run dev
```

Access the worker portal at:
**http://localhost:5173/worker.html**

### 4. Test Login

1. Open http://localhost:5173/worker.html
2. Enter:
   - Phone: The worker's phone number
   - PIN: Last 4 digits of phone (or custom PIN you set)
3. Click "Login"

You should see the worker dashboard! 🎉

---

## Verify Everything Works

### ✅ Backend Checklist

```bash
# 1. Check migrations
python manage.py showmigrations clients

# Should show:
# [X] 0011_add_worker_portal_models

# 2. Check worker accounts exist
python manage.py shell
>>> from clients.models_extensions import WorkerAccount
>>> WorkerAccount.objects.count()
1  # Should be > 0
>>> exit()

# 3. Test API endpoint
curl http://localhost:8000/api/worker/work-sites/
# Should return 401 (expected - needs auth)
```

### ✅ Frontend Checklist

1. Worker portal loads at `/worker.html`
2. Login form appears
3. Can login with valid credentials
4. Dashboard shows up after login
5. Navigation works (Dashboard, Assignments, Availability, Service Requests)

---

## Create Sample Data

### Create Work Sites

```python
python manage.py shell

from clients.models_extensions import WorkSite
from datetime import time

# Create some work sites
WorkSite.objects.create(
    name="Mission & 16th Pit Stop",
    site_type="pitstop",
    address="2675 16th Street, San Francisco, CA 94103",
    neighborhood="Mission District",
    supervisor_name="John Supervisor",
    supervisor_phone="415-555-0001",
    supervisor_email="john@example.com",
    typical_start_time=time(7, 0),
    typical_end_time=time(15, 0),
    available_time_slots=["6-12", "13-21"],
    max_workers_per_shift=2,
    is_active=True
)

WorkSite.objects.create(
    name="Civic Center Pit Stop",
    site_type="pitstop",
    address="50 UN Plaza, San Francisco, CA 94102",
    neighborhood="Civic Center",
    supervisor_name="Maria Manager",
    supervisor_phone="415-555-0002",
    typical_start_time=time(8, 0),
    typical_end_time=time(16, 0),
    available_time_slots=["6-12", "13-21", "22-5"],
    max_workers_per_shift=3,
    is_active=True
)

print("Created work sites!")
exit()
```

### Create Sample Assignment

```python
python manage.py shell

from clients.models_extensions import WorkAssignment, WorkSite
from clients.models import Client
from datetime import date, time, timedelta

client = Client.objects.first()
site = WorkSite.objects.first()

# Create assignment for tomorrow
WorkAssignment.objects.create(
    client=client,
    work_site=site,
    assignment_date=date.today() + timedelta(days=1),
    start_time=time(8, 0),
    end_time=time(16, 0),
    status='pending',
    assigned_by='Admin',
    assignment_notes='Please arrive 15 minutes early'
)

print("Created sample assignment!")
exit()
```

---

## Production Deployment

### Build Frontend

```bash
cd frontend
npm run build
```

This creates two HTML files in `dist/`:
- `index.html` - Client intake portal (existing)
- `worker.html` - Worker portal (new)

### Deploy to Azure

The existing deployment pipeline will automatically deploy both portals.

Both will be accessible at:
- Client Portal: `https://your-static-app.azurestaticapps.net/`
- Worker Portal: `https://your-static-app.azurestaticapps.net/worker.html`

---

## Common Issues & Solutions

### "Invalid phone number or PIN"
- Check that WorkerAccount exists for that phone
- Verify account is_active=True and is_approved=True
- Try resetting PIN to last 4 digits of phone in Admin
- Check account is not locked (locked_until field)

### "Account is pending approval"
- Go to Django Admin → Worker Accounts
- Find the account
- Check "Is Approved"
- Save

### "Failed to load dashboard"
- Check backend is running
- Check API URL in frontend config
- Open browser console for errors
- Verify session token exists: `localStorage.getItem('worker_token')`

### Frontend won't build
```bash
cd frontend
rm -rf node_modules
npm install
npm run build
```

---

## Next Steps

1. **Add More Workers:** Create accounts for all PitStop workers
2. **Set Up Work Sites:** Add all your locations
3. **Create Assignments:** Schedule workers
4. **Test Service Requests:** Have workers report issues
5. **Monitor Usage:** Check Django Admin for activity

---

## URLs Reference

**Local Development:**
- Backend Admin: http://localhost:8000/admin/
- Backend API: http://localhost:8000/api/
- Client Portal: http://localhost:5173/
- Worker Portal: http://localhost:5173/worker.html

**Production:**
- Backend Admin: https://mhh-client-backend-cuambzgeg3dfbphd.centralus-01.azurewebsites.net/admin/
- Backend API: https://mhh-client-backend-cuambzgeg3dfbphd.centralus-01.azurewebsites.net/api/
- Client Portal: https://brave-mud-077eb1810.1.azurestaticapps.net/
- Worker Portal: https://brave-mud-077eb1810.1.azurestaticapps.net/worker.html

---

## Management Commands

```bash
# Create worker account
python manage.py create_worker_account "415-555-1234" --approve

# Create admin user (if needed)
python manage.py create_admin

# Fix staff permissions
python manage.py fix_staff_permissions

# Send followup alerts
python manage.py send_followup_alerts
```

---

**🎉 That's it! Your worker portal is ready to use!**

For more details, see `WORKER_PORTAL_GUIDE.md`
