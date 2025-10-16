# Employment Desired Field Fix

## Problem Identified
The frontend and backend had a type mismatch for the `employment_desired` field in the Pit Stop Application:

### Before:
- **Backend**: `CharField` expecting a single string value (`'full_time'`, `'part_time'`, or `'relief_list'`)
- **Frontend**: Sending an array `[]` (e.g., `['full_time', 'part_time']`)

This caused Pit Stop applications to fail when submitting.

## Solution Implemented

### Backend Changes
Changed `employment_desired` field from `CharField` to `JSONField` to accept multiple selections:

**File**: `backend/clients/models.py` (line 351-354)
```python
employment_desired = models.JSONField(
    default=list,
    help_text='Employment types desired: ["full_time", "part_time", "relief_list"] - can select multiple'
)
```

### Migration Created
**File**: `backend/clients/migrations/0009_alter_pitstopapplication_employment_desired.py`

This migration changes the database schema to support array values.

### Frontend Status
The frontend was already correctly configured:
- Checkboxes allow multiple selections
- `employment_desired` is initialized as an empty array `[]`
- Form correctly sends array to backend

## User Experience Improvement
Users can now select multiple employment preferences:
- ✅ Full-time only
- ✅ Part-time only  
- ✅ Both full-time AND part-time (willing to take either)
- ✅ All three options (full-time, part-time, and relief list)

## Next Steps

### To Apply Changes:
1. Run the migration:
   ```bash
   cd backend
   python manage.py migrate --settings=config.simple_settings
   ```

2. Test the Pit Stop application form to ensure submissions work correctly

### Additional Notes
- The shift time slots in `weekly_schedule` JSONField already support arrays and work correctly
- No changes needed to the serializer or views - they automatically handle JSONField arrays

