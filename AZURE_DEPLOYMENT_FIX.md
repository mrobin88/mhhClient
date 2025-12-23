# Azure Deployment Fix Instructions

## Issues Fixed

1. ✅ **requirements.txt** - Copied to root so Azure Oryx can detect it
2. ✅ **startup.sh** - Created in root with proper pathing and settings
3. ✅ **Settings module** - Updated to use `config.settings` (auto-detects Azure)

## Azure Portal Configuration

### Option 1: Use the startup.sh script (Recommended)

In Azure Portal → App Service → Configuration → General Settings:

**Startup Command:**
```
bash startup.sh
```

### Option 2: Simple Gunicorn command

If the startup script doesn't work, use this simpler command:

**Startup Command:**
```
cd backend && python -m gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers 2 config.wsgi:application
```

**Important:** Make sure to set `DJANGO_SETTINGS_MODULE=config.settings` in Application Settings (not in the startup command).

## Application Settings Required

Make sure these are set in Azure Portal → Configuration → Application Settings:

- `DJANGO_SETTINGS_MODULE` = `config.settings`
- `SECRET_KEY` = (your secret key)
- `DATABASE_URL` or `DATABASE_PASSWORD` = (your database credentials)
- `WEBSITE_HOSTNAME` = (automatically set by Azure)

## What Changed

1. **requirements.txt** is now in both root and backend/ (Azure needs it in root for Oryx build)
2. **startup.sh** in root handles pathing, venv activation, and migrations
3. **config.settings** automatically detects Azure via WEBSITE_HOSTNAME
4. **.deployment** file tells Azure the project is in the backend/ subdirectory

## Next Steps

1. Push these changes to GitHub
2. Azure will auto-deploy (or trigger manual deployment)
3. Oryx should now detect requirements.txt and build dependencies
4. Check Azure Log Stream to verify Django is loading correctly

