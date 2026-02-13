# Fix for 500 Error on Admin Pages

## Problem
The admin pages (especially `/admin/clients/casenote/` and client-related pages) were returning 500 errors.

## Root Cause
I added `program_start_date` field and related computed properties to the Client model and admin, but the database migration **was not deployed to Azure** yet. When Django tried to access these non-existent fields, it caused database errors resulting in 500 responses.

## Immediate Fix Applied
I temporarily removed the `program_start_date` references from:
1. **`clients/admin.py`** - Removed from `list_display`, `list_filter`, `readonly_fields`, and fieldsets
2. **`clients/serializers.py`** - Removed computed fields like `days_in_program`, `program_duration_display`, etc.

These changes will fix the 500 errors immediately when deployed.

## Files Modified in This Fix
- `clients/admin.py` - Removed `program_start_date` and `program_duration` admin display
- `clients/serializers.py` - Removed program duration computed fields

## Next Steps to Deploy Program Start Date Feature

Once this fix is deployed and the site is working again, follow these steps to properly add the program start date feature:

### Step 1: Deploy Migration to Azure
```bash
# SSH into Azure App Service or use Kudu console
cd /home/site/wwwroot
source antenv/bin/activate  # or source env/bin/activate

# Run the migration
python3 manage.py migrate clients 0014

# Verify migration was applied
python3 manage.py showmigrations clients
```

### Step 2: Re-add Admin Fields
After migration is successfully applied, restore the admin configuration:

**In `clients/admin.py` - line 306:**
```python
list_display = ['full_name', 'phone', 'email', 'training_interest', 'status', 'program_start_date', 'program_duration', 'program_completed_date', 'job_placed', 'has_resume', 'case_notes_count', 'created_at']
```

**In `clients/admin.py` - line 307:**
```python
list_filter = ['status', 'training_interest', 'job_placed', 'neighborhood', 'sf_resident', 'employment_status', 'created_at', 'program_start_date', 'program_completed_date']
```

**In `clients/admin.py` - line 309:**
```python
readonly_fields = ['created_at', 'updated_at', 'case_notes_count', 'masked_ssn', 'resume_preview', 'program_duration_info']
```

**In `clients/admin.py` - line 384:**
```python
('Program Completion & Job Placement', {
    'fields': ('program_start_date', 'program_duration_info', 'program_completed_date', 'job_placed', 'job_placement_date', 'job_title', 'job_company', 'job_hourly_wage')
}),
```

### Step 3: Re-add Serializer Fields
**In `clients/serializers.py`:**
```python
class ClientSerializer(serializers.ModelSerializer):
    age = serializers.ReadOnlyField()
    full_name = serializers.ReadOnlyField()
    is_sf_resident = serializers.ReadOnlyField()
    has_resume = serializers.ReadOnlyField()
    case_notes_count = serializers.ReadOnlyField()
    resume_download_url = serializers.SerializerMethodField()
    resume_file_type = serializers.SerializerMethodField()
    days_in_program = serializers.ReadOnlyField()
    months_in_program = serializers.ReadOnlyField()
    program_duration_display = serializers.ReadOnlyField()
    is_in_program_one_year = serializers.ReadOnlyField()
```

### Step 4: Deploy Updated Code
Commit and push the restored admin configuration, which will trigger GitHub Actions to deploy.

## Important Lesson
⚠️ **Always deploy database migrations BEFORE deploying code that references new fields!**

The correct order is:
1. Create migration (locally)
2. Commit migration file
3. Deploy to Azure (migration runs automatically via startup.sh or manually)
4. Verify migration ran successfully
5. Deploy code that uses the new fields

## Files in This Repo
- `clients/migrations/0014_add_program_start_date.py` - The migration (ready to deploy)
- `PROGRAM_START_DATE_FEATURE.md` - Full documentation of the feature
- `FIX_500_ERROR.md` - This file

## Deployment Checklist
- [ ] Deploy this fix (removes program_start_date from admin)
- [ ] Verify site works (no 500 errors)
- [ ] SSH to Azure and run migration: `python3 manage.py migrate clients 0014`
- [ ] Verify migration succeeded
- [ ] Re-add admin fields (see Step 2 above)
- [ ] Re-add serializer fields (see Step 3 above)
- [ ] Commit and deploy
- [ ] Verify program_start_date feature works in admin

## Testing After Full Deployment
1. Go to Django Admin → Clients
2. Edit a client
3. Set "Program start date" field
4. Save and verify "Program Duration" shows in list view
5. Check API response includes program duration fields
