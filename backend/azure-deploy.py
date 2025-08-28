#!/usr/bin/env python3
"""
Azure Deployment Script for Django Backend
Deploys the Mission Hiring Hall Client System to Azure
"""

import os
import subprocess
import sys
from pathlib import Path

def run_command(command, description):
    """Run a shell command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"   Error: {e.stderr}")
        sys.exit(1)

def main():
    print("🚀 Deploying Mission Hiring Hall Client System to Azure...")
    print("=" * 60)
    
    # Check if we're in the backend directory
    backend_dir = Path(__file__).parent
    if not (backend_dir / "manage.py").exists():
        print("❌ Please run this script from the backend directory")
        sys.exit(1)
    
    # Install Azure CLI if not present
    print("🔍 Checking Azure CLI installation...")
    try:
        subprocess.run(["az", "--version"], check=True, capture_output=True)
        print("✅ Azure CLI is installed")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Azure CLI not found. Please install it first:")
        print("   https://docs.microsoft.com/en-us/cli/azure/install-azure-cli")
        sys.exit(1)
    
    # Check Azure login
    print("🔍 Checking Azure login status...")
    try:
        subprocess.run(["az", "account", "show"], check=True, capture_output=True)
        print("✅ Logged into Azure")
    except subprocess.CalledProcessError:
        print("❌ Not logged into Azure. Please run:")
        print("   az login")
        sys.exit(1)
    
    # Build the Django application
    print("\n📦 Building Django application...")
    run_command("pip install -r requirements.txt", "Installing dependencies")
    run_command("python manage.py collectstatic --noinput", "Collecting static files")
    run_command("python manage.py check --deploy", "Checking deployment readiness")
    
    # Create deployment package
    print("\n📋 Creating deployment package...")
    deployment_dir = backend_dir / "deployment"
    deployment_dir.mkdir(exist_ok=True)
    
    # Copy necessary files
    run_command(f"cp -r {backend_dir}/core {deployment_dir}/", "Copying core app")
    run_command(f"cp -r {backend_dir}/users {deployment_dir}/", "Copying users app")
    run_command(f"cp -r {backend_dir}/clients {deployment_dir}/", "Copying clients app")
    run_command(f"cp -r {backend_dir}/config {deployment_dir}/", "Copying config")
    run_command(f"cp {backend_dir}/manage.py {deployment_dir}/", "Copying manage.py")
    run_command(f"cp {backend_dir}/requirements.txt {deployment_dir}/", "Copying requirements")
    
    # Create startup command file for Azure
    startup_content = """#!/bin/bash
cd /home/site/wwwroot
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
gunicorn --bind=0.0.0.0 --timeout=600 config.wsgi:application
"""
    
    with open(deployment_dir / "startup.sh", "w") as f:
        f.write(startup_content)
    
    run_command(f"chmod +x {deployment_dir}/startup.sh", "Making startup script executable")
    
    # Create .deployment file for Azure
    deployment_config = """[config]
SCM_DO_BUILD_DURING_DEPLOYMENT=true
"""
    
    with open(deployment_dir / ".deployment", "w") as f:
        f.write(deployment_config)
    
    print("\n✅ Deployment package created successfully!")
    print(f"📁 Package location: {deployment_dir}")
    
    print("\n🚀 Next steps:")
    print("1. Run the Azure deployment script:")
    print("   ./azure-deploy.sh")
    print("2. Deploy the backend package to Azure Web App")
    print("3. Update frontend API endpoint")
    print("4. Test the complete system")
    
    print("\n💰 Profit calculation:")
    print("   Azure costs: $38/month (covered by nonprofit credits)")
    print("   Your charge: $400-600/month")
    print("   Pure profit: $362-562/month")

if __name__ == "__main__":
    main()
