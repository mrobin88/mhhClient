# Worker Dispatch & Reporting System

## Overview
Complete system for managing Pit Stop worker assignments, tracking availability, handling call-outs, and generating CSV reports for staff.

## New Models Created

### 1. **WorkSite**
- Tracks Pit Stop locations and special event sites
- Stores supervisor contact info
- Manages capacity limits (max workers per shift)
- Tracks shift times

### 2. **ClientAvailability**
- Weekly availability schedule for each client
- Day-by-day tracking (Monday-Sunday)
- Time ranges for availability
- Notes for special conditions

### 3. **WorkAssignment**
- Links clients to work sites for specific dates
- Status tracking: pending → confirmed → in_progress → completed
- Handles call-outs and replacements
- Tracks hours worked and performance

### 4. **CallOutLog**
- Detailed tracking of call-outs
- Records advance notice given
- Tracks replacement search efforts
- Follow-up actions

## CSV Export Reports

All reports accessible via Django admin or direct URLs:

### 1. **Available Workers Report**
**URL:** `/api/reports/available-workers/`
**Query params:**
- `?day=monday` - Filter by specific day
- `?date=2025-10-15` - Exclude already assigned for date

**Includes:**
- Name, phone, email
- Languages spoken
- Available days
- Recent performance (assignments, no-shows, call-outs)
- Notes

### 2. **Work Assignments Report**
**URL:** `/api/reports/assignments/`
**Query params:**
- `?start_date=2025-10-01&end_date=2025-10-31`
- `?site_id=1` - Filter by specific site
- `?status=confirmed` - Filter by status

**Includes:**
- Complete assignment details
- Worker contact info
- Site information
- Hours worked
- Call-out/replacement info

### 3. **Call-Out Report**
**URL:** `/api/reports/callouts/`
**Query params:**
- `?start_date=2025-09-01&end_date=2025-10-01`

**Includes:**
- Call-out details and timing
- Advance notice given
- Replacement search efforts
- Follow-up actions

### 4. **Today's Assignments** (Quick Access)
**URL:** `/api/reports/todays-assignments/`

**Includes:**
- All confirmed workers for today
- Organized by site
- Site supervisor contact info

## How Workers Use The System

### Morning Staff Workflow:

1. **Check Today's Assignments:**
   ```
   GET /api/reports/todays-assignments/
   ```
   Download CSV → print/distribute to supervisors

2. **If Someone Calls Out:**
   - Mark assignment as "called_out" in admin
   - Create Call Out Log entry
   - Download available workers:
     ```
     GET /api/reports/available-workers/?day=monday&date=2025-10-15
     ```
   - Call workers from CSV list
   - Assign replacement
   - Update Call Out Log

3. **Weekly Planning:**
   - Download assignments for next week
   - Download available workers by day
   - Make assignments in Django admin

### For Supervisor/Manager Reports:

1. **Monthly Performance:**
   ```
   GET /api/reports/assignments/?start_date=2025-09-01&end_date=2025-09-30
   ```

2. **Call-Out Analysis:**
   ```
   GET /api/reports/callouts/?start_date=2025-09-01&end_date=2025-09-30
   ```
   Identify patterns, repeated call-outs

## Next Steps To Implement

1. **Run migrations** to create new tables
2. **Add to admin.py** - admin interfaces for new models
3. **Add URL routes** - connect CSV views to URLs
4. **Add API endpoints** - RESTful API for mobile/web access
5. **Optional: Add SMS notifications** - auto-confirm assignments
6. **Optional: Add worker portal** - clients can view their schedule

## Implementation Commands

```bash
# 1. Create migration
cd backend
python manage.py makemigrations clients

# 2. Apply migration  
python manage.py migrate

# 3. Test in Django shell
python manage.py shell
from clients.models_extensions import WorkSite, WorkAssignment
site = WorkSite.objects.create(
    name="Mission & 16th Pit Stop",
    address="Mission St & 16th St, SF CA",
    neighborhood="Mission",
    typical_start_time="08:00",
    typical_end_time="16:00",
    max_workers_per_shift=2
)
```

## Future Enhancements

- **SMS Integration:** Auto-send assignment confirmations
- **Mobile App:** Workers can check schedule, confirm shifts
- **Auto-matching:** Suggest best workers based on availability + performance
- **Analytics Dashboard:** Visual reports of assignments, call-outs, performance
- **Payroll Integration:** Export hours worked for payroll processing

