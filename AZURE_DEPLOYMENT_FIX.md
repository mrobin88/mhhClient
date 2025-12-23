# Azure Deployment Fix Instructions

## The Problem

Django is not installed in the Python environment. The logs show:
- Gunicorn starts but can't import Django
- Virtual environment activation is failing silently
- Oryx build may not be installing dependencies

## Issues Fixed

1. ✅ **requirements.txt** - Copied to root so Azure Oryx can detect it
2. ✅ **startup.sh** - Enhanced with dependency installation and better error handling
3. ✅ **Settings module** - Updated to use `config.settings` (auto-detects Azure)
4. ✅ **build.sh** - Added build script for Oryx

## Azure Portal Configuration - CRITICAL

### Step 1: Update Startup Command

Go to: **Azure Portal → Your App Service → Configuration → General Settings**

**Find "Startup Command" and replace it with:**

```bash
bash /home/site/wwwroot/startup.sh
```

**OR use this direct command (if startup.sh doesn't work):**

```bash
cd /home/site/wwwroot/backend && source /home/site/wwwroot/antenv/bin/activate && pip install -r requirements.txt && export DJANGO_SETTINGS_MODULE=config.settings && python manage.py migrate --noinput && exec python -m gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers 2 config.wsgi:application
```

### Step 2: Verify Application Settings

In **Configuration → Application Settings**, ensure:

- `DJANGO_SETTINGS_MODULE` = `config.settings` (NOT `config.simple_settings`)
- `SCM_DO_BUILD_DURING_DEPLOYMENT` = `true` (if this setting exists)

### Step 3: Check Deployment Center

Go to **Deployment Center** and verify:
- Build provider is set correctly
- Oryx should detect `requirements.txt` in root and build automatically

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

