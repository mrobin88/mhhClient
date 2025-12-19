# 🚨 URGENT: Fix Backend Startup - Run These Commands NOW

## The Problem
Azure can't find `backend/startup.sh` - the path is wrong.

## Solution: Use Direct Command Instead

Run this in Azure Cloud Shell:

```bash
# Use direct command instead of file path
az webapp config set \
  --resource-group mhh-client-rg \
  --name mhh-client-backend \
  --startup-file "bash -c 'cd /home/site/wwwroot && if [ -d backend ]; then cd backend; fi && export DJANGO_SETTINGS_MODULE=config.simple_settings && timeout 30 python manage.py migrate --noinput --settings=config.simple_settings 2>&1 || true && exec gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers 2 config.wsgi:application'"

# Restart
az webapp restart --resource-group mhh-client-rg --name mhh-client-backend
```

## Alternative: Try Different Paths

If that doesn't work, try these startup commands one by one:

### Option 1: Just startup.sh (if backend is root)
```bash
az webapp config set \
  --resource-group mhh-client-rg \
  --name mhh-client-backend \
  --startup-file "startup.sh"
```

### Option 2: Absolute path
```bash
az webapp config set \
  --resource-group mhh-client-rg \
  --name mhh-client-backend \
  --startup-file "/home/site/wwwroot/backend/startup.sh"
```

### Option 3: Direct command (safest)
```bash
az webapp config set \
  --resource-group mhh-client-rg \
  --name mhh-client-backend \
  --startup-file "bash -c 'cd /home/site/wwwroot/backend 2>/dev/null || cd /home/site/wwwroot && export DJANGO_SETTINGS_MODULE=config.simple_settings && python manage.py migrate --noinput --settings=config.simple_settings && exec gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers 2 config.wsgi:application'"
```

## Check What Files Are Actually Deployed

```bash
# SSH into the container to see what's there
az webapp ssh --name mhh-client-backend --resource-group mhh-client-rg

# Then in SSH:
ls -la /home/site/wwwroot/
ls -la /home/site/wwwroot/backend/ 2>/dev/null || echo "No backend directory"
find /home/site/wwwroot -name "startup.sh" -o -name "manage.py"
```

## Quick Test

After setting startup command, wait 30 seconds, then:

```bash
curl https://mhh-client-backend-cuambzgeg3dfbphd.centralus-01.azurewebsites.net/admin/
```

Should return 200 OK or redirect to login.

