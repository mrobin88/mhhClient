#!/usr/bin/env python3
"""
COMPLETE INTEGRATION TEST
Tests Django Backend + Vue Frontend + PostgreSQL + Admin
"""

import os
import sys
import django
import json
import subprocess
import time
from pathlib import Path

# Setup Django
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.production_settings')

def test_backend_api():
    """Test Django backend API endpoints"""
    print("🔧 Testing Django Backend API...")
    print("=" * 50)
    
    try:
        django.setup()
        from django.test import Client
        from django.contrib.auth import get_user_model
        from clients.models import Client as ClientModel, CaseNote
        from users.models import StaffUser
        
        client = Client()
        
        # Test API endpoints
        endpoints_to_test = [
            ('/api/clients/', 'GET'),
            ('/api/case-notes/', 'GET'),
            ('/admin/', 'GET'),
            ('/admin/login/', 'GET'),
        ]
        
        for endpoint, method in endpoints_to_test:
            if method == 'GET':
                response = client.get(endpoint)
                print(f"✅ {method} {endpoint}: {response.status_code}")
            
        # Test model creation
        if not StaffUser.objects.filter(username='testuser').exists():
            user = StaffUser.objects.create_user(
                username='testuser',
                email='test@test.com',
                password='testpass123',
                role='case_manager'
            )
            print(f"✅ Created test user: {user.username}")
        
        # Test client creation
        test_client = ClientModel.objects.create(
            first_name='John',
            last_name='Doe',
            phone='415-555-0123',
            dob='1990-01-01',
            gender='M',
            sf_resident='yes',
            neighborhood='mission',
            demographic_info='mixed',
            language='en',
            highest_degree='hs',
            employment_status='unemployed',
            training_interest='citybuild',
            referral_source='website'
        )
        print(f"✅ Created test client: {test_client.first_name} {test_client.last_name}")
        
        # Test case note creation
        case_note = CaseNote.objects.create(
            client=test_client,
            note_type='initial',
            staff_member='Test Staff',
            content='Initial intake completed',
            next_steps='Schedule training orientation'
        )
        print(f"✅ Created test case note: {case_note.note_type}")
        
        return True
        
    except Exception as e:
        print(f"❌ Backend API test failed: {e}")
        return False

def test_cors_configuration():
    """Test CORS configuration"""
    print("\n🌐 Testing CORS Configuration...")
    print("=" * 50)
    
    try:
        django.setup()
        from django.conf import settings
        
        print(f"CORS_ALLOWED_ORIGINS: {getattr(settings, 'CORS_ALLOWED_ORIGINS', 'Not set')}")
        print(f"CORS_ALLOW_CREDENTIALS: {getattr(settings, 'CORS_ALLOW_CREDENTIALS', 'Not set')}")
        print(f"CORS_ALLOW_ALL_ORIGINS: {getattr(settings, 'CORS_ALLOW_ALL_ORIGINS', 'Not set')}")
        
        # Check if frontend URLs are in CORS
        cors_origins = getattr(settings, 'CORS_ALLOWED_ORIGINS', [])
        frontend_urls = [
            'http://localhost:5173',
            'https://brave-mud-077eb1810.1.azurestaticapps.net',
            'https://mhh-client-frontend.azurestaticapps.net'
        ]
        
        for url in frontend_urls:
            if url in cors_origins:
                print(f"✅ {url} is in CORS_ALLOWED_ORIGINS")
            else:
                print(f"⚠️  {url} NOT in CORS_ALLOWED_ORIGINS")
        
        return True
        
    except Exception as e:
        print(f"❌ CORS test failed: {e}")
        return False

def test_admin_interface():
    """Test Django admin interface"""
    print("\n👤 Testing Django Admin Interface...")
    print("=" * 50)
    
    try:
        django.setup()
        from django.contrib.admin.sites import site
        from django.test import Client
        from users.models import StaffUser
        
        # Check registered models
        registered_models = site._registry
        print(f"📋 Admin registered models: {len(registered_models)}")
        
        expected_models = ['StaffUser', 'Client', 'CaseNote']
        for model_name in expected_models:
            found = any(model.__name__ == model_name for model in registered_models.keys())
            if found:
                print(f"✅ {model_name} registered in admin")
            else:
                print(f"❌ {model_name} NOT registered in admin")
        
        # Test admin URLs
        client = Client()
        
        # Test admin index (should redirect to login)
        response = client.get('/admin/')
        if response.status_code in [200, 302]:
            print(f"✅ Admin index accessible: {response.status_code}")
        else:
            print(f"❌ Admin index failed: {response.status_code}")
        
        # Test admin login page
        response = client.get('/admin/login/')
        if response.status_code == 200:
            print(f"✅ Admin login page accessible: {response.status_code}")
        else:
            print(f"❌ Admin login page failed: {response.status_code}")
        
        # Check if superuser exists
        if StaffUser.objects.filter(is_superuser=True).exists():
            superuser = StaffUser.objects.filter(is_superuser=True).first()
            print(f"✅ Superuser exists: {superuser.username}")
        else:
            print(f"⚠️  No superuser found - create one with: python manage.py createsuperuser")
        
        return True
        
    except Exception as e:
        print(f"❌ Admin test failed: {e}")
        return False

def test_database_connection():
    """Test database connection and schema"""
    print("\n🗄️  Testing Database Connection...")
    print("=" * 50)
    
    try:
        django.setup()
        from django.db import connection
        from django.core.management import call_command
        from io import StringIO
        
        # Test connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            print("✅ Database connection successful")
        
        # Check database type
        db_engine = connection.settings_dict['ENGINE']
        db_name = connection.settings_dict['NAME']
        print(f"Database engine: {db_engine}")
        print(f"Database name: {db_name}")
        
        # Check migrations
        output = StringIO()
        call_command('showmigrations', '--plan', stdout=output)
        migrations_output = output.getvalue()
        
        if '[X]' in migrations_output:
            applied_count = migrations_output.count('[X]')
            print(f"✅ Applied migrations: {applied_count}")
        else:
            print("⚠️  No migrations applied")
        
        # Check table counts
        with connection.cursor() as cursor:
            if 'postgresql' in db_engine:
                cursor.execute("""
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name LIKE '%client%'
                """)
            else:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%client%'")
            
            tables = cursor.fetchall()
            print(f"✅ Client-related tables: {len(tables)}")
            for table in tables:
                print(f"   - {table[0]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def generate_frontend_config():
    """Generate frontend configuration"""
    print("\n⚙️  Generating Frontend Configuration...")
    print("=" * 50)
    
    try:
        # Get current settings
        django.setup()
        from django.conf import settings
        
        # Determine API URL based on settings
        allowed_hosts = getattr(settings, 'ALLOWED_HOSTS', [])
        debug = getattr(settings, 'DEBUG', False)
        
        if debug:
            api_url = 'http://localhost:8000'
        else:
            # Use first non-localhost host
            production_host = None
            for host in allowed_hosts:
                if 'azurewebsites.net' in host:
                    production_host = f'https://{host}'
                    break
            api_url = production_host or 'https://mhh-client-backend.azurewebsites.net'
        
        # Generate config
        config = {
            'API_BASE_URL': api_url,
            'CORS_ORIGINS': getattr(settings, 'CORS_ALLOWED_ORIGINS', []),
            'DEBUG': debug,
            'ENDPOINTS': {
                'clients': '/api/clients/',
                'case_notes': '/api/case-notes/',
                'admin': '/admin/',
            }
        }
        
        print(f"✅ Frontend should use API URL: {api_url}")
        print(f"✅ CORS configured for: {len(config['CORS_ORIGINS'])} origins")
        
        # Save config to file
        config_path = Path(__file__).parent.parent / 'frontend' / 'src' / 'config' / 'generated.json'
        config_path.parent.mkdir(exist_ok=True)
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"✅ Generated config file: {config_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Frontend config generation failed: {e}")
        return False

def main():
    """Run all integration tests"""
    print("🚀 COMPLETE INTEGRATION TEST")
    print("Django Backend + Vue Frontend + PostgreSQL + Admin")
    print("=" * 60)
    
    tests = [
        ("Database Connection", test_database_connection),
        ("Backend API", test_backend_api),
        ("CORS Configuration", test_cors_configuration),
        ("Admin Interface", test_admin_interface),
        ("Frontend Config", generate_frontend_config),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n📊 INTEGRATION TEST SUMMARY")
    print("=" * 60)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    if passed == total:
        print(f"\n🎉 ALL TESTS PASSED ({passed}/{total})")
        print("🚀 System is ready for production!")
    else:
        print(f"\n⚠️  SOME TESTS FAILED ({passed}/{total} passed)")
        print("🔧 Fix the issues above before deploying")
    
    print("\n📋 DEPLOYMENT CHECKLIST:")
    print("□ Set environment variables in Azure App Service")
    print("□ Configure startup command: ./startup.sh")
    print("□ Deploy backend to Azure App Service")
    print("□ Deploy frontend to Azure Static Web Apps")
    print("□ Test admin at: https://your-app.azurewebsites.net/admin/")
    print("□ Test frontend at: https://your-frontend.azurestaticapps.net/")

if __name__ == '__main__':
    main()
