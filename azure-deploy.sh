#!/bin/bash

# Azure Deployment Script for Mission Hiring Hall Client System
# This script sets up the complete Azure infrastructure

set -e

echo "🚀 Deploying Mission Hiring Hall Client System to Azure..."

# Configuration
RESOURCE_GROUP="mhh-client-rg"
LOCATION="westus2"
APP_SERVICE_PLAN="mhh-app-plan"
WEB_APP_NAME="mhh-backend-api"
STATIC_WEB_APP="mhh-frontend"
POSTGRES_SERVER="mhh-postgres-server"
POSTGRES_DB="mhh_client_db"
POSTGRES_USER="mhh_admin"
POSTGRES_PASSWORD=$(openssl rand -base64 32)

echo "📍 Location: $LOCATION"
echo "🏗️  Resource Group: $RESOURCE_GROUP"

# Create Resource Group
echo "📦 Creating Resource Group..."
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create App Service Plan (Basic B1 - $13/month)
echo "📋 Creating App Service Plan..."
az appservice plan create \
    --name $APP_SERVICE_PLAN \
    --resource-group $RESOURCE_GROUP \
    --sku B1 \
    --is-linux

# Create PostgreSQL Server
echo "🗄️  Creating PostgreSQL Database Server..."
az postgres flexible-server create \
    --resource-group $RESOURCE_GROUP \
    --name $POSTGRES_SERVER \
    --admin-user $POSTGRES_USER \
    --admin-password $POSTGRES_PASSWORD \
    --sku-name Standard_B1ms \
    --tier Burstable \
    --storage-size 32 \
    --version 14

# Create Database
echo "📊 Creating Database..."
az postgres flexible-server db create \
    --resource-group $RESOURCE_GROUP \
    --server-name $POSTGRES_SERVER \
    --database-name $POSTGRES_DB

# Configure PostgreSQL Firewall (allow Azure services)
echo "🔥 Configuring Database Firewall..."
az postgres flexible-server firewall-rule create \
    --resource-group $RESOURCE_GROUP \
    --name $POSTGRES_SERVER \
    --rule-name "AllowAzureServices" \
    --start-ip-address 0.0.0.0 \
    --end-ip-address 0.0.0.0

# Create Web App for Django Backend
echo "🌐 Creating Django Web App..."
az webapp create \
    --resource-group $RESOURCE_GROUP \
    --plan $APP_SERVICE_PLAN \
    --name $WEB_APP_NAME \
    --runtime "PYTHON:3.9"

# Configure Web App Environment Variables
echo "⚙️  Configuring Web App Environment..."
az webapp config appsettings set \
    --resource-group $RESOURCE_GROUP \
    --name $WEB_APP_NAME \
    --settings \
    DATABASE_NAME=$POSTGRES_DB \
    DATABASE_USER=$POSTGRES_USER \
    DATABASE_PASSWORD=$POSTGRES_PASSWORD \
    DATABASE_HOST="$POSTGRES_SERVER.postgres.database.azure.com" \
    DATABASE_PORT=5432 \
    DEBUG=False \
    ALLOWED_HOSTS="$WEB_APP_NAME.azurewebsites.net" \
    CORS_ALLOWED_ORIGINS="https://$STATIC_WEB_APP.azurestaticapps.net"

# Create Static Web App for Vue Frontend
echo "🎨 Creating Static Web App for Frontend..."
az staticwebapp create \
    --name $STATIC_WEB_APP \
    --resource-group $RESOURCE_GROUP \
    --source https://github.com/yourusername/mhhClient \
    --branch main \
    --app-location frontend \
    --api-location backend

echo "✅ Azure Infrastructure Deployed Successfully!"
echo ""
echo "📋 Resource Summary:"
echo "   Resource Group: $RESOURCE_GROUP"
echo "   Backend API: https://$WEB_APP_NAME.azurewebsites.net"
echo "   Frontend: https://$STATIC_WEB_APP.azurestaticapps.net"
echo "   Database: $POSTGRES_SERVER.postgres.database.azure.com"
echo ""
echo "🔑 Database Credentials:"
echo "   Username: $POSTGRES_USER"
echo "   Password: $POSTGRES_PASSWORD"
echo "   Database: $POSTGRES_DB"
echo ""
echo "💰 Estimated Monthly Cost: $38 (covered by nonprofit credits)"
echo "💵 Your Profit: Charge $400-600/month for managed services"
echo ""
echo "🚀 Next Steps:"
echo "   1. Deploy your code to the Web App"
echo "   2. Update frontend API endpoint"
echo "   3. Test the complete system"
echo "   4. Start billing for managed services!"
