# Azure Permission Check Script
# Run this in PowerShell as Administrator

Write-Host "🔍 Checking Azure Setup and Permissions..." -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green

# Check Azure CLI installation
try {
    $azVersion = az --version 2>$null
    if ($azVersion) {
        Write-Host "✅ Azure CLI is installed" -ForegroundColor Green
        Write-Host "   Version: $($azVersion[0])" -ForegroundColor Gray
    }
} catch {
    Write-Host "❌ Azure CLI not found" -ForegroundColor Red
    Write-Host "   Install with: winget install Microsoft.AzureCLI" -ForegroundColor Yellow
    exit 1
}

# Check Azure login
try {
    $account = az account show 2>$null | ConvertFrom-Json
    if ($account) {
        Write-Host "✅ Logged into Azure" -ForegroundColor Green
        Write-Host "   Subscription: $($account.name)" -ForegroundColor Gray
        Write-Host "   Tenant: $($account.tenantId)" -ForegroundColor Gray
    }
} catch {
    Write-Host "❌ Not logged into Azure" -ForegroundColor Red
    Write-Host "   Run: az login" -ForegroundColor Yellow
    exit 1
}

# Check resource group permissions
$resourceGroup = "mhh-client-rg"
Write-Host "`n🔐 Checking permissions on resource group: $resourceGroup" -ForegroundColor Cyan

try {
    $assignments = az role assignment list --assignee $account.user.name --resource-group $resourceGroup --output json 2>$null | ConvertFrom-Json
    
    if ($assignments) {
        Write-Host "✅ Role assignments found:" -ForegroundColor Green
        foreach ($assignment in $assignments) {
            Write-Host "   Role: $($assignment.roleDefinitionName)" -ForegroundColor Gray
        }
    } else {
        Write-Host "❌ No role assignments found" -ForegroundColor Red
        Write-Host "   You need Contributor or Owner role on this resource group" -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ Cannot check permissions - resource group may not exist" -ForegroundColor Red
}

# Check if resource group exists
try {
    $rg = az group show --name $resourceGroup --output json 2>$null | ConvertFrom-Json
    if ($rg) {
        Write-Host "✅ Resource group exists" -ForegroundColor Green
        Write-Host "   Location: $($rg.location)" -ForegroundColor Gray
    }
} catch {
    Write-Host "❌ Resource group '$resourceGroup' does not exist" -ForegroundColor Red
    Write-Host "   Create it first or check the name" -ForegroundColor Yellow
}

Write-Host "`n📋 Next Steps:" -ForegroundColor Cyan
Write-Host "1. If you don't have permissions, ask your Azure admin to grant you Contributor role" -ForegroundColor White
Write-Host "2. If resource group doesn't exist, create it first" -ForegroundColor White
Write-Host "3. Run the deployment script again" -ForegroundColor White

Write-Host "`n🔗 Useful Commands:" -ForegroundColor Cyan
Write-Host "   az login" -ForegroundColor Gray
Write-Host "   az group create --name $resourceGroup --location centralus" -ForegroundColor Gray
Write-Host "   az role assignment create --assignee $($account.user.name) --role Contributor --resource-group $resourceGroup" -ForegroundColor Gray 