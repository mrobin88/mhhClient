# Azure Deployment Guide for Mission Hiring Hall Client System

This guide will help you deploy your Django + Vue.js application to Azure using App Service and Static Web Apps.

## Prerequisites

1. **Azure Account** with active subscription
2. **GitHub Repository** with your code
3. **Azure CLI** installed locally (optional but recommended)

## Database Setup

You're currently using **PostgreSQL** locally via Docker Compose. For Azure, you'll need to set up Azure Database for PostgreSQL.

### Option 1: Azure Database for PostgreSQL (Recommended)

1. **Create PostgreSQL Server:**
   ```bash
   az postgres server create \
           --resource-group mhh-client-rg \
     --name mhh-postgres-server \
           --location centralus \
      --admin-user mhhsupport \
           --admin-password "Support1048!" \
     --sku-name GP_Gen5_2
   ```

2. **Create Database:**
   ```bash
   az postgres db create \
           --resource-group mhh-client-rg \
     --server-name mhh-postgres-server \
     --name mhh_client_db
   ```

3. **Configure Firewall:**
   ```bash
   az postgres server firewall-rule create \
           --resource-group mhh-client-rg \
     --server mhh-postgres-server \
     --name AllowAzureServices \
     --start-ip-address 0.0.0.0 \
     --end-ip-address 0.0.0.0
   ```

### Option 2: Containerized Database (Alternative)

If you prefer to keep using containers, you can deploy to Azure Container Instances or use Azure Database for PostgreSQL Flexible Server.

## Backend Deployment (Azure App Service)

### Step 1: Create App Service

1. **Via Azure Portal:**
   - Go to Azure Portal → Create a resource → Web App
   - Choose Python 3.11 runtime
   - Create new resource group: `mhh-client-rg`
   - App name: `mhh-backend-api`
   - Region: East US (or your preferred region)

2. **Via Azure CLI:**
   ```bash
   az webapp create \
           --resource-group mhh-client-rg \
     --plan mhh-app-service-plan \
     --name mhh-backend-api \
     --runtime "PYTHON|3.11"
   ```

### Step 2: Configure Environment Variables

In Azure Portal → App Service → Configuration → Application settings, add:

```env
SECRET_KEY=your-super-secret-key-here
DEBUG=False
DJANGO_SETTINGS_MODULE=config.azure_settings
DATABASE_NAME=mhh_client_db
DATABASE_USER=mhh_admin@mhh-postgres-server
DATABASE_PASSWORD=Support1048!
DATABASE_HOST=mhh-postgres-server.postgres.database.azure.com
DATABASE_PORT=5432
CORS_ALLOWED_ORIGINS=https://mhh-frontend.azurestaticapps.net
ALLOWED_HOSTS=mhh-backend-api.azurewebsites.net
```

### Step 3: Set up GitHub Actions

1. **Get Publish Profile:**
   - Go to App Service → Deployment Center → Local Git/FTPS credentials
   - Download the publish profile

2. **Add GitHub Secrets:**
   - Go to your GitHub repo → Settings → Secrets and variables → Actions
   - Add secret: `AZUREAPPSERVICE_PUBLISHPROFILE` with the content of your publish profile

3. **Deploy:**
   - Push to main branch
   - GitHub Actions will automatically deploy your backend

## Frontend Deployment (Azure Static Web Apps)

### Step 1: Create Static Web App

1. **Via Azure Portal:**
   - Go to Azure Portal → Create a resource → Static Web App
   - Resource group: `mhh-client-rg`
   - Name: `mhh-frontend`
   - Source: GitHub
   - Connect your repository
   - Build details:
     - App location: `/frontend`
     - Output location: `dist`
     - API location: (leave empty)

2. **Via Azure CLI:**
   ```bash
   az staticwebapp create \
     --name mhh-frontend \
           --resource-group mhh-client-rg \
     --source https://github.com/yourusername/yourrepo \
     --location "Central US" \
     --branch main \
     --app-location "/frontend" \
     --output-location "dist"
   ```

### Step 2: Configure Build Settings

The GitHub Actions workflow will automatically:
- Install Node.js dependencies
- Build the Vue.js application
- Deploy to Azure Static Web Apps

### Step 3: Update API Endpoint

The frontend will automatically use the Azure backend URL when deployed. For local development, create a `.env.local` file:

```env
VITE_API_URL=http://localhost:8000
```

## Containerized Deployment (Alternative)

If you prefer containerized deployment:

### Step 1: Create Dockerfiles

**Backend Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN python manage.py collectstatic --noinput

EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "config.wsgi:application"]
```

**Frontend Dockerfile:**
```dockerfile
FROM node:18-alpine as build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### Step 2: Deploy to Azure Container Registry

```bash
# Create ACR
az acr create --resource-group mhh-rg --name mhhacr --sku Basic

# Build and push images
az acr build --registry mhhacr --image mhh-backend:latest ./backend
az acr build --registry mhhacr --image mhh-frontend:latest ./frontend
```

### Step 3: Deploy to Container Instances

```bash
# Deploy backend
az container create \
        --resource-group mhh-client-rg \
  --name mhh-backend \
  --image mhhacr.azurecr.io/mhh-backend:latest \
  --cpu 1 \
  --memory 1 \
  --ports 8000 \
  --environment-variables \
    SECRET_KEY=your-secret-key \
    DATABASE_HOST=mhh-postgres-server.postgres.database.azure.com \
    DATABASE_NAME=mhh_client_db \
    DATABASE_USER=mhh_admin@mhh-postgres-server \
    DATABASE_PASSWORD=Support1048!
```

## Cost Estimation

### App Service + Static Web Apps (Recommended)
- **App Service (B1)**: ~$13/month
- **Static Web Apps**: Free tier (2GB bandwidth)
- **PostgreSQL (Basic)**: ~$25/month
- **Total**: ~$38/month

### Container Instances (Alternative)
- **Container Instances**: ~$30/month
- **Container Registry**: ~$5/month
- **PostgreSQL (Basic)**: ~$25/month
- **Total**: ~$60/month

## Monitoring and Logging

1. **Application Insights** (Optional):
   - Add to your App Service for monitoring
   - Provides performance insights and error tracking

2. **Log Analytics**:
   - Monitor application logs
   - Set up alerts for errors

## Security Considerations

1. **Environment Variables**: Never commit secrets to Git
2. **HTTPS**: Both App Service and Static Web Apps use HTTPS by default
3. **CORS**: Configured to only allow your frontend domain
4. **Database**: Use SSL connections and strong passwords

## Troubleshooting

### Common Issues:

1. **Database Connection Errors**:
   - Check firewall rules
   - Verify connection string format
   - Ensure SSL is enabled

2. **Static Files Not Loading**:
   - Run `python manage.py collectstatic`
   - Check WhiteNoise configuration

3. **CORS Errors**:
   - Update `CORS_ALLOWED_ORIGINS` in Azure settings
   - Check frontend URL matches exactly

4. **Build Failures**:
   - Check GitHub Actions logs
   - Verify all dependencies are in requirements.txt

## Next Steps

1. **Set up monitoring** with Application Insights
2. **Configure custom domain** for production
3. **Set up automated backups** for the database
4. **Implement CI/CD** for staging environment
5. **Add SSL certificates** for custom domains

## Support

For issues with this deployment:
1. Check Azure App Service logs
2. Review GitHub Actions workflow runs
3. Verify environment variables are set correctly
4. Test database connectivity

Your Mission Hiring Hall Client System should now be running on Azure! 🚀