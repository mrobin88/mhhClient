# Program Start Date Feature

## Overview

Added a `program_start_date` field to track when clients begin their program and calculate how long they've been enrolled. This helps identify clients who have been in the program for one year or more.

## What Was Added

### 1. Database Field
**Field:** `program_start_date` (DateField, optional)
- Located in: `clients/models.py` → `Client` model
- Help text: "Date when client started their program"
- Nullable: Yes (allows blank for existing clients)
- Position: In "Program Completion & Job Placement Tracking" section

### 2. Calculated Properties

#### `days_in_program`
```python
client.days_in_program  # Returns: 365 (or None if no start date)
```
Returns the number of days between `program_start_date` and either:
- `program_completed_date` (if program is completed)
- Today's date (if program is still active)

#### `months_in_program`
```python
client.months_in_program  # Returns: 12.0 (or None if no start date)
```
Converts days to approximate months (30.44 days per month average).

#### `program_duration_display`
```python
client.program_duration_display  # Returns: "1 year, 2 months"
```
Human-readable duration formatted as:
- `"15 days"` - for programs under 1 month
- `"3 months"` - for programs under 1 year
- `"1 year, 2 months"` - for programs over 1 year
- `"Not started"` - if no start date set

#### `is_in_program_one_year`
```python
client.is_in_program_one_year  # Returns: True or False
```
Boolean check for clients who have been in the program for 365+ days.

### 3. Admin Interface Updates

#### List View
- **New column:** `Program Duration` - Shows duration with 🎉 emoji for 1+ year clients
- **Filter added:** Can filter by `program_start_date` (date range)
- **Sortable:** Click column header to sort by start date

#### Edit View
- **Field location:** "Program Completion & Job Placement" section (first field)
- **Date picker:** Standard Django date picker widget
- **Info display:** Shows calculated program duration with visual formatting:
  ```
  Started: February 3, 2025
  Duration: 8 months (243 days)
  Currently active in program
  ```
- **1+ year indicator:** Green checkmark for clients in program 1+ year

### 4. API Updates

The `ClientSerializer` now includes these read-only fields:

```json
{
  "id": 1,
  "full_name": "John Doe",
  "program_start_date": "2024-02-03",
  "days_in_program": 365,
  "months_in_program": 12.0,
  "program_duration_display": "1 year",
  "is_in_program_one_year": true,
  "program_completed_date": null,
  ...
}
```

## Usage Examples

### Admin Interface

#### Setting Program Start Date
1. Go to Django Admin → Clients
2. Click on a client to edit
3. Scroll to "Program Completion & Job Placement" section
4. Set the "Program start date" field
5. Save - the duration will calculate automatically

#### Finding 1+ Year Clients
1. Go to Django Admin → Clients
2. Look for entries with 🎉 emoji in "Program Duration" column
3. Or use filters: "By program start date" → select date range

#### Batch Operations
You can create admin actions to:
- Mark all clients starting on a specific date
- Export list of 1+ year clients
- Generate anniversary reports

### API Usage

#### Get Client with Program Duration
```python
GET /api/clients/1/

Response:
{
  "id": 1,
  "program_start_date": "2024-02-03",
  "program_duration_display": "1 year",
  "is_in_program_one_year": true,
  ...
}
```

#### Filter Clients by Start Date
```python
GET /api/clients/?program_start_date__gte=2024-01-01

# Returns all clients who started program on or after Jan 1, 2024
```

#### Check 1+ Year Clients in Code
```python
from clients.models import Client

# Get all clients in program for 1+ year
long_term_clients = [c for c in Client.objects.all() if c.is_in_program_one_year]

# Or use annotation for efficient DB query
from django.db.models import F, ExpressionWrapper, fields
from datetime import date, timedelta

one_year_ago = date.today() - timedelta(days=365)
long_term = Client.objects.filter(
    program_start_date__lte=one_year_ago
).exclude(
    program_start_date__isnull=True
)
```

### Python Shell Examples

```python
from clients.models import Client
from datetime import date

# Set program start date for a client
client = Client.objects.get(id=1)
client.program_start_date = date(2024, 2, 3)
client.save()

# Check how long they've been in program
print(f"Days: {client.days_in_program}")
print(f"Months: {client.months_in_program}")
print(f"Display: {client.program_duration_display}")
print(f"1+ year? {client.is_in_program_one_year}")

# Find all clients who started in 2024
clients_2024 = Client.objects.filter(
    program_start_date__year=2024
)

# Find clients approaching 1 year (350-365 days)
from datetime import timedelta
approaching_one_year = []
for client in Client.objects.exclude(program_start_date__isnull=True):
    if client.days_in_program and 350 <= client.days_in_program < 365:
        approaching_one_year.append(client)

print(f"Clients approaching 1-year: {len(approaching_one_year)}")
```

## Migration

**File:** `clients/migrations/0014_add_program_start_date.py`

The migration:
- Adds the `program_start_date` field to the `Client` model
- Field is nullable (allows NULL for existing clients)
- No data migration needed (existing clients will have NULL start date)

### Running the Migration

**Production (Azure App Service):**
```bash
# SSH into Azure
python3 manage.py migrate clients 0014

# Or via Kudu console
cd /home/site/wwwroot
source antenv/bin/activate
python3 manage.py migrate clients 0014
```

**Local Development:**
```bash
python manage.py migrate clients 0014
```

### Populating Historical Data

If you need to set start dates for existing clients:

```python
from clients.models import Client
from datetime import date

# Example: Set start date based on created_at
for client in Client.objects.filter(program_start_date__isnull=True):
    # Use created_at as approximation
    client.program_start_date = client.created_at.date()
    client.save()

# Or set specific dates for clients
client = Client.objects.get(id=1)
client.program_start_date = date(2024, 1, 15)
client.save()
```

## Reporting Ideas

### 1-Year Anniversary Report
```python
from clients.models import Client
import csv

with open('one_year_clients.csv', 'w') as f:
    writer = csv.writer(f)
    writer.writerow(['Name', 'Start Date', 'Duration', 'Days', 'Status'])
    
    for client in Client.objects.exclude(program_start_date__isnull=True):
        if client.is_in_program_one_year:
            writer.writerow([
                client.full_name,
                client.program_start_date,
                client.program_duration_display,
                client.days_in_program,
                client.status
            ])
```

### Monthly Cohort Analysis
```python
from clients.models import Client
from collections import defaultdict

cohorts = defaultdict(list)
for client in Client.objects.exclude(program_start_date__isnull=True):
    cohort_key = client.program_start_date.strftime('%Y-%m')
    cohorts[cohort_key].append(client)

for cohort, clients in sorted(cohorts.items()):
    print(f"\n{cohort}: {len(clients)} clients")
    completed = sum(1 for c in clients if c.program_completed_date)
    placed = sum(1 for c in clients if c.job_placed)
    print(f"  Completed: {completed}")
    print(f"  Job Placed: {placed}")
```

## Files Modified

1. **`clients/models.py`**
   - Added `program_start_date` field
   - Added `days_in_program` property
   - Added `months_in_program` property
   - Added `program_duration_display` property
   - Added `is_in_program_one_year` property

2. **`clients/admin.py`**
   - Added `program_start_date` to list_display
   - Added `program_duration` column method with 1+ year highlighting
   - Added `program_duration_info` readonly field for edit view
   - Added `program_start_date` to list_filter
   - Updated fieldsets to include new field

3. **`clients/serializers.py`**
   - Added program duration fields to `ClientSerializer`

4. **`clients/migrations/0014_add_program_start_date.py`**
   - New migration file

## Testing Checklist

- [ ] Run migration in development/staging
- [ ] Add program start date to a test client
- [ ] Verify duration displays correctly in admin list view
- [ ] Verify duration info shows in admin edit view
- [ ] Test with client who has completed program (uses completion date)
- [ ] Test with client still in program (uses today's date)
- [ ] Test with client without start date (shows "Not started")
- [ ] Verify API includes new fields
- [ ] Test 1+ year indicator shows for clients 365+ days
- [ ] Test sorting by program start date
- [ ] Test filtering by program start date

## Future Enhancements

Consider adding:
- **Anniversary alerts** - Email notifications when clients reach 1 year
- **Cohort dashboard** - Visual analytics by start date cohorts
- **Automated start date** - Set `program_start_date = created_at` on client creation
- **Program duration goals** - Track expected vs actual program length
- **Milestone tracking** - 3 months, 6 months, 9 months, 12 months checkpoints
