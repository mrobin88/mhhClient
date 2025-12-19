# 🚨 URGENT: Fix Backend Admin - Run These Now

## Quick Fix Commands (Copy & Paste in Azure Cloud Shell)

```bash
# 1. Set startup script (fixed version)
az webapp config set \
  --resource-group mhh-client-rg \
  --name mhh-client-backend \
  --startup-file "backend/startup.sh"

# 2. Sync latest code from GitHub
az webapp deployment source sync \
  --resource-group mhh-client-rg \
  --name mhh-client-backend

# 3. Restart immediately
az webapp restart \
  --resource-group mhh-client-rg \
  --name mhh-client-backend

# 4. Check if it's working (wait 30 seconds first)
sleep 30
curl -I https://mhh-client-backend-cuambzgeg3dfbphd.centralus-01.azurewebsites.net/admin/
```

## If Still Not Working - Check Logs

```bash
# View recent error logs
az webapp log show \
  --resource-group mhh-client-rg \
  --name mhh-client-backend \
  --tail 100
```

## Alternative: Simple Startup Command (if script fails)

If the startup script still fails, use this direct command:

```bash
az webapp config set \
  --resource-group mhh-client-rg \
  --name mhh-client-backend \
  --startup-file "bash -c 'cd /home/site/wwwroot/backend && export DJANGO_SETTINGS_MODULE=config.simple_settings && python manage.py migrate --noinput --settings=config.simple_settings && python manage.py collectstatic --noinput --settings=config.simple_settings && exec gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers 2 config.wsgi:application'"
```

Then restart:
```bash
az webapp restart --resource-group mhh-client-rg --name mhh-client-backend
```

