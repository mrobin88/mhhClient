# Azure Deployment Commands

## Quick Deploy Script

I've created a deployment script for you. Run this in **Azure Cloud Shell**:

```bash
# Download and run the deployment script
curl -o deploy-to-azure.sh https://raw.githubusercontent.com/mrobin88/mhhClient/main/deploy-to-azure.sh
chmod +x deploy-to-azure.sh
./deploy-to-azure.sh
```

Or run these commands manually:

## Manual Deployment Steps

### 1. Set Startup Script
```bash
az webapp config set \
  --resource-group mhh-client-rg \
  --name mhh-client-backend \
  --startup-file "backend/startup.sh"
```

### 2. Sync Code from GitHub
```bash
az webapp deployment source sync \
  --resource-group mhh-client-rg \
  --name mhh-client-backend
```

### 3. Restart App Service
```bash
az webapp restart \
  --resource-group mhh-client-rg \
  --name mhh-client-backend
```

### 4. Check Logs
```bash
az webapp log tail \
  --resource-group mhh-client-rg \
  --name mhh-client-backend
```

## What Happens

1. ✅ Startup script set to `backend/startup.sh`
2. ✅ Code synced from GitHub
3. ✅ App restarts
4. ✅ `startup.sh` runs automatically:
   - Runs migrations: `python manage.py migrate`
   - Collects static files: `python manage.py collectstatic`
   - Starts Gunicorn server

## Verify Deployment

After deployment, check:
- Admin actions appear: Go to Admin → Case Notes → Actions dropdown
- Should see: "Export selected case notes to CSV"
- Should see: "Send follow-up alert emails for selected case notes"

## Troubleshooting

If actions still don't appear:

1. **Hard refresh browser**: `Ctrl+Shift+R` or `Cmd+Shift+R`
2. **Check if code deployed**: 
   ```bash
   az webapp deployment list --name mhh-client-backend --resource-group mhh-client-rg --query "[0].{Time:startTime, Status:status}" --output table
   ```
3. **Check logs for errors**:
   ```bash
   az webapp log show --name mhh-client-backend --resource-group mhh-client-rg --tail 50
   ```

