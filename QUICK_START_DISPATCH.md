# Quick Start: Worker Dispatch System

## What You Just Got

✅ **4 New Database Models:**
- `WorkSite` - Pit Stop locations
- `ClientAvailability` - When clients can work
- `WorkAssignment` - Assign clients to sites
- `CallOutLog` - Track call-outs and replacements

✅ **4 CSV Export Reports:**
- Available workers (with filters)
- Work assignments (date range)
- Call-out analysis
- Today's quick list

✅ **Full URL Routes** configured

## To Activate (3 Commands):

```bash
cd /Users/matthewrobin/Projects/mhhClient/backend

# 1. Create database tables
python manage.py makemigrations clients

# 2. Apply to database
python manage.py migrate

# 3. Optional: Create sample data
python manage.py shell
```

## Test It Immediately:

### Create First Work Site:
```python
from clients.models_extensions import WorkSite

site = WorkSite.objects.create(
    name="Mission & 16th Pit Stop",
    address="Mission St & 16th St",
    neighborhood="Mission",
    typical_start_time="08:00:00",
    typical_end_time="16:00:00",
    max_workers_per_shift=2,
    supervisor_name="John Supervisor",
    supervisor_phone="415-555-1234"
)
```

### Set Client Availability:
```python
from clients.models import Client
from clients.models_extensions import ClientAvailability

client = Client.objects.first()  # Get any client

# Mark available Monday-Friday
for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']:
    ClientAvailability.objects.create(
        client=client,
        day_of_week=day,
        available=True,
        start_time="08:00:00",
        end_time="17:00:00"
    )
```

### Create Assignment:
```python
from datetime import date, time
from clients.models_extensions import WorkAssignment

assignment = WorkAssignment.objects.create(
    client=client,
    work_site=site,
    assignment_date=date.today(),
    start_time=time(8, 0),
    end_time=time(16, 0),
    status='confirmed',
    assigned_by='Your Name'
)
```

## Use The CSV Reports:

### In Browser (Login Required):
```
https://your-backend/api/reports/todays-assignments/
https://your-backend/api/reports/available-workers/?day=monday
https://your-backend/api/reports/assignments/?start_date=2025-10-01&end_date=2025-10-31
https://your-backend/api/reports/callouts/?start_date=2025-09-01
```

### Or via curl:
```bash
# Today's assignments
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://your-backend/api/reports/todays-assignments/ \
  -o todays_workers.csv

# Available workers for Monday
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "https://your-backend/api/reports/available-workers/?day=monday" \
  -o monday_available.csv
```

## Typical Daily Workflow:

### Morning (8 AM):
1. Download: `/api/reports/todays-assignments/`
2. Print and give to supervisors
3. Contact workers to confirm

### If Call-Out (Anytime):
1. Log call-out in Django admin
2. Download: `/api/reports/available-workers/?day=monday&date=2025-10-15`
3. Call workers from list
4. Assign replacement
5. Update call-out log

### End of Week:
1. Download: `/api/reports/assignments/?start_date=...&end_date=...`
2. Review hours worked
3. Generate payroll data

### Monthly Reports:
1. Download: `/api/reports/callouts/?start_date=...&end_date=...`
2. Analyze patterns
3. Follow up with frequent call-outs

## Need Django Admin?

Add to `backend/clients/admin.py`:

```python
from .models_extensions import WorkSite, ClientAvailability, WorkAssignment, CallOutLog

@admin.register(WorkSite)
class WorkSiteAdmin(admin.ModelAdmin):
    list_display = ['name', 'neighborhood', 'max_workers_per_shift', 'is_active']
    list_filter = ['is_active', 'site_type', 'neighborhood']
    search_fields = ['name', 'address']

@admin.register(ClientAvailability)
class ClientAvailabilityAdmin(admin.ModelAdmin):
    list_display = ['client', 'day_of_week', 'available', 'start_time', 'end_time']
    list_filter = ['day_of_week', 'available']
    search_fields = ['client__first_name', 'client__last_name']

@admin.register(WorkAssignment)
class WorkAssignmentAdmin(admin.ModelAdmin):
    list_display = ['client', 'work_site', 'assignment_date', 'status', 'confirmed_by_client']
    list_filter = ['status', 'assignment_date', 'work_site']
    search_fields = ['client__first_name', 'client__last_name']
    date_hierarchy = 'assignment_date'

@admin.register(CallOutLog)
class CallOutLogAdmin(admin.ModelAdmin):
    list_display = ['assignment', 'reported_at', 'advance_notice_hours', 'replacement_found_at']
    list_filter = ['reported_at', 'client_contacted_after']
```

## Questions?

See `WORKER_DISPATCH_SYSTEM.md` for full documentation.

