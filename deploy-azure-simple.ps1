# Simple Azure Deployment Script
# Run this in PowerShell as Administrator

param(
    [string]$ResourceGroup = "mhh-client-rg",
    [string]$Location = "centralus"
)

Write-Host "🚀 Simple Azure Deployment for MHH Client System" -ForegroundColor Green
Write-Host "=================================================" -ForegroundColor Green

# Function to check if command succeeded
function Test-Command {
    param($Command, $Description)
    try {
        Invoke-Expression $Command | Out-Null
        Write-Host "✅ $Description" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "❌ $Description failed" -ForegroundColor Red
        return $false
    }
}

# Check Azure CLI
if (-not (Test-Command "az --version" "Azure CLI check")) {
    Write-Host "Installing Azure CLI..." -ForegroundColor Yellow
    winget install Microsoft.AzureCLI
    Write-Host "Please restart PowerShell and run this script again" -ForegroundColor Yellow
    exit 1
}

# Check Azure login
if (-not (Test-Command "az account show" "Azure login check")) {
    Write-Host "Please login to Azure first:" -ForegroundColor Yellow
    Write-Host "az login" -ForegroundColor White
    exit 1
}

# Get current user
$currentUser = az account show --query user.name -o tsv
Write-Host "Logged in as: $currentUser" -ForegroundColor Cyan

# Check if resource group exists
$rgExists = az group show --name $ResourceGroup --output json 2>$null
if (-not $rgExists) {
    Write-Host "Creating resource group: $ResourceGroup" -ForegroundColor Yellow
    if (Test-Command "az group create --name $ResourceGroup --location $Location" "Resource group creation") {
        Write-Host "Resource group created successfully" -ForegroundColor Green
    } else {
        Write-Host "Failed to create resource group. Check your permissions." -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "Resource group exists: $ResourceGroup" -ForegroundColor Green
}

# Check permissions on resource group
$hasPermission = $false
try {
    $assignments = az role assignment list --assignee $currentUser --resource-group $ResourceGroup --output json 2>$null | ConvertFrom-Json
    foreach ($assignment in $assignments) {
        if ($assignment.roleDefinitionName -in @("Contributor", "Owner")) {
            $hasPermission = $true
            Write-Host "✅ You have $($assignment.roleDefinitionName) role" -ForegroundColor Green
            break
        }
    }
} catch {
    Write-Host "Could not check permissions" -ForegroundColor Yellow
}

if (-not $hasPermission) {
    Write-Host "❌ You need Contributor or Owner role on the resource group" -ForegroundColor Red
    Write-Host "`n🔧 Solutions:" -ForegroundColor Yellow
    Write-Host "1. Ask your Azure admin to grant you Contributor role" -ForegroundColor White
    Write-Host "2. Or try to grant yourself the role (if you have Owner on subscription):" -ForegroundColor White
    Write-Host "   az role assignment create --assignee $currentUser --role Contributor --resource-group $ResourceGroup" -ForegroundColor Gray
    
    $grantSelf = Read-Host "`nTry to grant yourself Contributor role? (y/n)"
    if ($grantSelf -eq "y") {
        if (Test-Command "az role assignment create --assignee $currentUser --role Contributor --resource-group $ResourceGroup" "Role assignment") {
            Write-Host "✅ Role assigned successfully!" -ForegroundColor Green
            $hasPermission = $true
        } else {
            Write-Host "❌ Failed to assign role. Contact your Azure admin." -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "Please contact your Azure admin to get Contributor role" -ForegroundColor Yellow
        exit 1
    }
}

# Now proceed with deployment
Write-Host "`n🚀 Starting deployment..." -ForegroundColor Green

# Create App Service Plan
Write-Host "Creating App Service Plan..." -ForegroundColor Yellow
if (Test-Command "az appservice plan create --name mhh-app-service-plan --resource-group $ResourceGroup --location $Location --sku B1 --is-linux" "App Service Plan creation") {
    Write-Host "App Service Plan created" -ForegroundColor Green
}

# Create PostgreSQL server
Write-Host "Creating PostgreSQL server..." -ForegroundColor Yellow
$postgresServer = "mhh-client-postgres"
$postgresPassword = "Support1048!"

if (Test-Command "az postgres server create --resource-group $ResourceGroup --name $postgresServer --location $Location --admin-user mhhsupport --admin-password $postgresPassword --sku-name GP_Gen5_2" "PostgreSQL server creation") {
    Write-Host "PostgreSQL server created" -ForegroundColor Green
    
    # Create database
    if (Test-Command "az postgres db create --resource-group $ResourceGroup --server-name $postgresServer --name mhh_client_db" "Database creation") {
        Write-Host "Database created" -ForegroundColor Green
    }
    
    # Configure firewall
    if (Test-Command "az postgres server firewall-rule create --resource-group $ResourceGroup --server $postgresServer --name AllowAzureServices --start-ip-address 0.0.0.0 --end-ip-address 0.0.0.0" "Firewall configuration") {
        Write-Host "Firewall configured" -ForegroundColor Green
    }
}

# Create App Service
Write-Host "Creating App Service..." -ForegroundColor Yellow
$appServiceName = "mhh-client-backend"

if (Test-Command "az webapp create --resource-group $ResourceGroup --plan mhh-app-service-plan --name $appServiceName --runtime 'PYTHON|3.11'" "App Service creation") {
    Write-Host "App Service created" -ForegroundColor Green
    
    # Configure environment variables
    $secretKey = [System.Web.Security.Membership]::GeneratePassword(50, 10)
    $envVars = @(
        "SECRET_KEY=$secretKey",
        "DEBUG=False",
        "DJANGO_SETTINGS_MODULE=config.azure_settings",
        "DATABASE_NAME=mhh_client_db",
        "DATABASE_USER=mhhsupport@$postgresServer",
        "DATABASE_PASSWORD=$postgresPassword",
        "DATABASE_HOST=$postgresServer.postgres.database.azure.com",
        "DATABASE_PORT=5432"
    )
    
    $envVarsString = $envVars -join " "
    if (Test-Command "az webapp config appsettings set --resource-group $ResourceGroup --name $appServiceName --settings $envVarsString" "Environment variables configuration") {
        Write-Host "Environment variables configured" -ForegroundColor Green
    }
}

Write-Host "`n🎉 Deployment completed!" -ForegroundColor Green
Write-Host "=================================" -ForegroundColor Green
Write-Host "Resource Group: $ResourceGroup" -ForegroundColor White
Write-Host "App Service: $appServiceName" -ForegroundColor White
Write-Host "PostgreSQL: $postgresServer" -ForegroundColor White
Write-Host "Database: mhh_client_db" -ForegroundColor White

Write-Host "`n📋 Next Steps:" -ForegroundColor Cyan
Write-Host "1. Set up GitHub Actions deployment" -ForegroundColor White
Write-Host "2. Create Static Web App for frontend" -ForegroundColor White
Write-Host "3. Test your backend API" -ForegroundColor White

Write-Host "`n🔗 URLs:" -ForegroundColor Cyan
Write-Host "Backend: https://$appServiceName.azurewebsites.net" -ForegroundColor White
Write-Host "Azure Portal: https://portal.azure.com" -ForegroundColor White 