#!/usr/bin/env python3
"""
PRODUCTION DEPLOYMENT SCRIPT
Sets up PostgreSQL + Vue + Django Admin on Azure
"""

import os
import sys
import subprocess
from pathlib import Path

def run_command(command, description):
    """Run a shell command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed")
        if result.stdout.strip():
            print(f"   Output: {result.stdout.strip()}")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"   Error: {e.stderr}")
        return None

def check_production_setup():
    """Check if production environment is properly configured"""
    print("🔍 Checking Production Setup...")
    print("=" * 50)
    
    required_env_vars = [
        'DATABASE_NAME',
        'DATABASE_USER', 
        'DATABASE_PASSWORD',
        'DATABASE_HOST',
        'SECRET_KEY'
    ]
    
    missing_vars = []
    for var in required_env_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        else:
            display_value = "***HIDDEN***" if "PASSWORD" in var or "SECRET" in var else value
            print(f"✅ {var}: {display_value}")
    
    if missing_vars:
        print(f"\n❌ Missing environment variables: {', '.join(missing_vars)}")
        print("\n🛠️  Set these in Azure App Service → Configuration → Application settings:")
        for var in missing_vars:
            if var == 'SECRET_KEY':
                print(f"   {var}=<generate-a-50-character-random-string>")
            elif var == 'DATABASE_PASSWORD':
                print(f"   {var}=<your-postgres-password-from-azure>")
            else:
                print(f"   {var}=<value>")
        return False
    
    return True

def test_database_connection():
    """Test PostgreSQL connection"""
    print("\n🗄️  Testing PostgreSQL Connection...")
    print("=" * 50)
    
    os.environ['DJANGO_SETTINGS_MODULE'] = 'config.production_settings'
    
    try:
        import django
        django.setup()
        
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            print(f"✅ PostgreSQL connected: {version}")
            return True
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("\n🔧 Troubleshooting:")
        print("   1. Check DATABASE_PASSWORD is set correctly")
        print("   2. Verify PostgreSQL server allows connections from Azure")
        print("   3. Check firewall rules in Azure PostgreSQL")
        return False

def run_migrations():
    """Run database migrations"""
    print("\n📋 Running Database Migrations...")
    print("=" * 50)
    
    commands = [
        ("python manage.py makemigrations --settings=config.production_settings", "Creating migrations"),
        ("python manage.py migrate --settings=config.production_settings", "Applying migrations"),
    ]
    
    for command, description in commands:
        result = run_command(command, description)
        if result is None:
            return False
    
    return True

def collect_static_files():
    """Collect static files for production"""
    print("\n📁 Collecting Static Files...")
    print("=" * 50)
    
    result = run_command(
        "python manage.py collectstatic --noinput --settings=config.production_settings",
        "Collecting static files"
    )
    return result is not None

def create_superuser_if_needed():
    """Create superuser if none exists"""
    print("\n👤 Checking Superuser...")
    print("=" * 50)
    
    try:
        os.environ['DJANGO_SETTINGS_MODULE'] = 'config.production_settings'
        import django
        django.setup()
        
        from users.models import StaffUser
        
        if not StaffUser.objects.filter(is_superuser=True).exists():
            print("⚠️  No superuser found. You'll need to create one:")
            print("   python manage.py createsuperuser --settings=config.production_settings")
            return False
        else:
            superuser = StaffUser.objects.filter(is_superuser=True).first()
            print(f"✅ Superuser exists: {superuser.username}")
            return True
            
    except Exception as e:
        print(f"❌ Superuser check failed: {e}")
        return False

def generate_startup_script():
    """Generate Azure startup script"""
    print("\n🚀 Generating Azure Startup Script...")
    print("=" * 50)
    
    startup_content = '''#!/bin/bash
# Azure App Service Startup Script for Django
set -e

echo "🚀 Starting Mission Hiring Hall Backend..."

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Run migrations
echo "📋 Running migrations..."
python manage.py migrate --settings=config.production_settings

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput --settings=config.production_settings

# Start Gunicorn
echo "🌐 Starting Gunicorn server..."
gunicorn --bind=0.0.0.0:8000 --timeout=600 --workers=2 --worker-class=sync config.wsgi:application
'''
    
    with open('startup.sh', 'w') as f:
        f.write(startup_content)
    
    run_command("chmod +x startup.sh", "Making startup script executable")
    print("✅ Startup script created: startup.sh")
    
    print("\n📋 Azure Configuration:")
    print("   1. Go to Azure Portal → App Service → Configuration → General settings")
    print("   2. Set Startup Command to: ./startup.sh")
    print("   3. Set Python version to: 3.11")

def test_admin_functionality():
    """Test Django admin functionality"""
    print("\n🔧 Testing Django Admin...")
    print("=" * 50)
    
    try:
        os.environ['DJANGO_SETTINGS_MODULE'] = 'config.production_settings'
        import django
        django.setup()
        
        from django.contrib.admin.sites import site
        from django.test import Client
        
        # Check registered models
        registered_models = site._registry
        print(f"📋 Admin registered models: {len(registered_models)}")
        for model, admin_class in registered_models.items():
            print(f"   - {model.__name__}")
        
        # Test admin URLs
        client = Client()
        response = client.get('/admin/')
        print(f"🔗 Admin URL test: {response.status_code} (302 = redirect to login, expected)")
        
        response = client.get('/admin/login/')
        print(f"🔑 Admin login test: {response.status_code} (200 = success)")
        
        return True
        
    except Exception as e:
        print(f"❌ Admin test failed: {e}")
        return False

def main():
    """Main deployment function"""
    print("🚀 PRODUCTION DEPLOYMENT - Mission Hiring Hall")
    print("PostgreSQL + Vue Frontend + Django Admin")
    print("=" * 60)
    
    # Change to backend directory
    backend_dir = Path(__file__).parent
    os.chdir(backend_dir)
    
    # Run all checks and setup
    steps = [
        ("Environment Check", check_production_setup),
        ("Database Connection", test_database_connection),
        ("Database Migrations", run_migrations),
        ("Static Files", collect_static_files),
        ("Superuser Check", create_superuser_if_needed),
        ("Admin Functionality", test_admin_functionality),
    ]
    
    results = []
    for step_name, step_func in steps:
        try:
            result = step_func()
            results.append((step_name, result))
        except Exception as e:
            print(f"❌ {step_name} failed with exception: {e}")
            results.append((step_name, False))
    
    # Generate startup script regardless of test results
    generate_startup_script()
    
    # Summary
    print("\n📊 DEPLOYMENT SUMMARY")
    print("=" * 60)
    
    for step_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {step_name}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    if passed == total:
        print(f"\n🎉 ALL CHECKS PASSED ({passed}/{total})")
        print("🚀 Ready for Azure deployment!")
    else:
        print(f"\n⚠️  SOME ISSUES FOUND ({passed}/{total} passed)")
        print("🔧 Fix the issues above before deploying to Azure")
    
    print("\n📋 NEXT STEPS:")
    print("1. Fix any failed checks above")
    print("2. Set environment variables in Azure App Service")
    print("3. Deploy code to Azure")
    print("4. Configure startup command: ./startup.sh")
    print("5. Test admin at: https://your-app.azurewebsites.net/admin/")

if __name__ == '__main__':
    main()
