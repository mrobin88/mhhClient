# How to Run the Employment Desired Migration

## What Was Fixed
The Pit Stop Application form was failing because:
1. **Backend** expected a single employment type (string)
2. **Frontend** was sending multiple selections (array)

## Changes Made
1. ✅ Updated `backend/clients/models.py` - changed `employment_desired` to JSONField
2. ✅ Created migration file: `backend/clients/migrations/0009_alter_pitstopapplication_employment_desired.py`
3. ✅ Frontend already correctly configured with checkboxes and array

## To Apply the Migration

### Option 1: Using your existing Python environment
```bash
cd backend
python manage.py migrate clients --settings=config.simple_settings
```

### Option 2: Using Python 3 directly
```bash
cd backend
python3 manage.py migrate clients --settings=config.simple_settings
```

### Option 3: Using virtual environment (if you have one)
```bash
cd backend
source venv/bin/activate  # or wherever your venv is
python manage.py migrate clients --settings=config.simple_settings
```

## Verify the Migration
After running the migration, check it worked:
```bash
cd backend
python manage.py showmigrations clients --settings=config.simple_settings
```

You should see:
```
clients
  [X] 0001_initial
  [X] 0002_auto_20250815_2255
  ...
  [X] 0008_auto_20251008_1545
  [X] 0009_alter_pitstopapplication_employment_desired
```

## Test the Fix
1. Start your Django backend
2. Open the frontend client form
3. Select "Pit Stop Program" as training interest
4. Check MULTIPLE employment desired options (e.g., Full-time AND Part-time)
5. Fill out the rest and submit
6. It should now save successfully!

## Rollback (if needed)
If something goes wrong, you can rollback:
```bash
cd backend
python manage.py migrate clients 0008 --settings=config.simple_settings
```

## Production Deployment
When deploying to production:
```bash
cd backend
python manage.py migrate clients --settings=config.production_settings
```

