# Azure Deployment Checklist

## ✅ **What You Have (Good Job!)**
- [x] Environment variables configured in Azure portal
- [x] Database credentials set up
- [x] Resource group created
- [x] App Service created

## ❌ **What's Missing (This is why it's not working)**

### 1. **Startup Command Configuration**
**Problem**: Azure doesn't know how to start your Python app
**Solution**: In Azure Portal → App Service → Configuration → General settings → Startup Command
```
gunicorn --bind=0.0.0.0 --timeout=600 --workers=2 config.wsgi:application
```

### 2. **Python Version Configuration**
**Problem**: Azure might be using wrong Python version
**Solution**: In Azure Portal → App Service → Configuration → General settings → Stack settings
- Stack: Python
- Major version: 3.11
- Minor version: 3.11

### 3. **GitHub Actions Setup**
**Problem**: No automatic deployment when you push code
**Solution**: Add these secrets to your GitHub repo:
- `AZUREAPPSERVICE_PUBLISHPROFILE` (from App Service → Deployment Center)
- `AZURE_STATIC_WEB_APPS_API_TOKEN` (from Static Web App → Manage deployment tokens)

### 4. **Static Web App Creation**
**Problem**: Frontend not deployed
**Solution**: Create Static Web App in Azure Portal:
- Name: `mhh-client-frontend`
- Source: GitHub
- App location: `/frontend`
- Output location: `dist`

## 🔧 **Quick Fix Steps**

### Step 1: Configure Startup Command
1. Go to Azure Portal → App Service → `mhh-client-backend`
2. Configuration → General settings
3. Set **Startup Command** to:
   ```
   gunicorn --bind=0.0.0.0 --timeout=600 --workers=2 config.wsgi:application
   ```
4. Save

### Step 2: Verify Python Version
1. Configuration → General settings
2. Stack settings:
   - Stack: Python
   - Major version: 3.11
   - Minor version: 3.11

### Step 3: Test Backend
1. Go to your App Service URL: `https://mhh-client-backend.azurewebsites.net`
2. You should see Django or your API response

### Step 4: Set Up GitHub Actions
1. Go to your GitHub repo → Settings → Secrets and variables → Actions
2. Add `AZUREAPPSERVICE_PUBLISHPROFILE`
3. Get the publish profile from Azure Portal → App Service → Deployment Center → Local Git/FTPS credentials

### Step 5: Create Static Web App
1. Azure Portal → Create a resource → Static Web App
2. Connect to your GitHub repo
3. Set app location to `/frontend`
4. Set output location to `dist`

## 🚨 **Common Issues & Solutions**

### Issue: "Application Error" or "Service Unavailable"
**Cause**: Wrong startup command or Python version
**Solution**: Check startup command and Python version in App Service settings

### Issue: Database Connection Error
**Cause**: Environment variables not set correctly
**Solution**: Verify all environment variables in App Service Configuration

### Issue: Static Files Not Loading
**Cause**: Missing `collectstatic` or wrong static file configuration
**Solution**: Add to startup command or run manually

### Issue: CORS Errors
**Cause**: Frontend URL not in CORS allowed origins
**Solution**: Update `CORS_ALLOWED_ORIGINS` in environment variables

## 📋 **Environment Variables Checklist**
Make sure these are set in Azure Portal → App Service → Configuration:

```env
SECRET_KEY=your-secret-key
DEBUG=False
DJANGO_SETTINGS_MODULE=config.azure_settings
DATABASE_NAME=mhh_client_db
DATABASE_USER=mhhsupport@mhh-client-postgres
DATABASE_PASSWORD=your-password
DATABASE_HOST=mhh-client-postgres.postgres.database.azure.com
DATABASE_PORT=5432
CORS_ALLOWED_ORIGINS=https://mhh-client-frontend.azurestaticapps.net
ALLOWED_HOSTS=mhh-client-backend.azurewebsites.net
```

## 🎯 **Test Your Deployment**

### Backend Test
```bash
curl https://mhh-client-backend.azurewebsites.net/api/
```

### Frontend Test
```bash
curl https://mhh-client-frontend.azurestaticapps.net/
```

## 🚀 **Next Steps After Fixing**
1. Push code to GitHub main branch
2. GitHub Actions will automatically deploy
3. Test both backend and frontend
4. Set up custom domain (optional)
5. Configure monitoring and alerts

## 💡 **Pro Tips**
- Use Azure Application Insights for monitoring
- Set up staging environment for testing
- Configure automated backups for database
- Use Azure Key Vault for sensitive secrets
- Set up SSL certificates for custom domains 