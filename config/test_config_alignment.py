"""
Configuration alignment tests to prevent mismatches between settings files
"""
import os
import sys
import django
from django.test import TestCase
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class ConfigAlignmentTests(TestCase):
    """Test that all configuration files are properly aligned"""
    
    def setUp(self):
        """Set up test environment"""
        self.original_env = os.environ.copy()
    
    def tearDown(self):
        """Clean up test environment"""
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_simple_settings_imports_correctly(self):
        """Test that simple_settings can be imported without errors"""
        try:
            from config import simple_settings
            self.assertTrue(hasattr(simple_settings, 'SECRET_KEY'))
            self.assertTrue(hasattr(simple_settings, 'DATABASES'))
            self.assertTrue(hasattr(simple_settings, 'INSTALLED_APPS'))
        except ImportError as e:
            self.fail(f"Failed to import simple_settings: {e}")
    
    def test_production_settings_imports_correctly(self):
        """Test that production_settings can be imported without errors"""
        try:
            from config import production_settings
            self.assertTrue(hasattr(production_settings, 'SECRET_KEY'))
            self.assertTrue(hasattr(production_settings, 'DATABASES'))
            self.assertTrue(hasattr(production_settings, 'INSTALLED_APPS'))
        except ImportError as e:
            self.fail(f"Failed to import production_settings: {e}")
    
    def test_installed_apps_alignment(self):
        """Test that both settings files have the same core apps"""
        from config import simple_settings, production_settings
        
        # Core apps that should be in both
        core_apps = [
            'django.contrib.admin',
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.messages',
            'django.contrib.staticfiles',
            'rest_framework',
            'django_filters',
            'core',
            'users.apps.UsersConfig',
            'clients',
            'corsheaders',
            'storages',  # Should be in both for Azure Blob Storage
        ]
        
        for app in core_apps:
            self.assertIn(app, simple_settings.INSTALLED_APPS, 
                         f"App {app} missing from simple_settings.INSTALLED_APPS")
            self.assertIn(app, production_settings.INSTALLED_APPS, 
                         f"App {app} missing from production_settings.INSTALLED_APPS")
    
    def test_azure_storage_configuration(self):
        """Test Azure Blob Storage configuration alignment"""
        from config import simple_settings, production_settings
        
        # Test that both settings have Azure storage configuration
        self.assertTrue(hasattr(simple_settings, 'DEFAULT_FILE_STORAGE'))
        self.assertTrue(hasattr(production_settings, 'DEFAULT_FILE_STORAGE'))
        
        # Test that both can handle Azure storage when credentials are present
        os.environ['AZURE_ACCOUNT_NAME'] = 'testaccount'
        os.environ['AZURE_ACCOUNT_KEY'] = 'testkey'
        
        # Reload settings to pick up environment variables
        import importlib
        importlib.reload(simple_settings)
        importlib.reload(production_settings)
        
        # Both should use Azure storage when credentials are present
        self.assertEqual(simple_settings.DEFAULT_FILE_STORAGE, 'clients.storage.AzurePrivateStorage')
        self.assertEqual(production_settings.DEFAULT_FILE_STORAGE, 'clients.storage.AzurePrivateStorage')
        
        # Both should have Azure settings
        self.assertEqual(simple_settings.AZURE_ACCOUNT_NAME, 'testaccount')
        self.assertEqual(production_settings.AZURE_ACCOUNT_NAME, 'testaccount')
        self.assertEqual(simple_settings.AZURE_ACCOUNT_KEY, 'testkey')
        self.assertEqual(production_settings.AZURE_ACCOUNT_KEY, 'testkey')
    
    def test_database_configuration_alignment(self):
        """Test that database configuration is consistent"""
        from config import simple_settings, production_settings
        
        # Both should have database configuration
        self.assertIn('default', simple_settings.DATABASES)
        self.assertIn('default', production_settings.DATABASES)
        
        # Both should support PostgreSQL
        simple_db = simple_settings.DATABASES['default']
        prod_db = production_settings.DATABASES['default']
        
        # Test that both can handle PostgreSQL configuration
        os.environ['DATABASE_PASSWORD'] = 'testpassword'
        os.environ['DATABASE_NAME'] = 'testdb'
        os.environ['DATABASE_USER'] = 'testuser'
        os.environ['DATABASE_HOST'] = 'testhost'
        
        # Reload settings
        import importlib
        importlib.reload(simple_settings)
        importlib.reload(production_settings)
        
        # Both should use PostgreSQL when password is provided
        self.assertEqual(simple_settings.DATABASES['default']['ENGINE'], 
                        'django.db.backends.postgresql')
        self.assertEqual(production_settings.DATABASES['default']['ENGINE'], 
                        'django.db.backends.postgresql')
    
    def test_cors_configuration_alignment(self):
        """Test CORS configuration is consistent"""
        from config import simple_settings, production_settings
        
        # Both should have CORS configuration
        self.assertTrue(hasattr(simple_settings, 'CORS_ALLOWED_ORIGINS'))
        self.assertTrue(hasattr(production_settings, 'CORS_ALLOWED_ORIGINS'))
        
        # Both should have CSRF trusted origins
        self.assertTrue(hasattr(simple_settings, 'CSRF_TRUSTED_ORIGINS'))
        self.assertTrue(hasattr(production_settings, 'CSRF_TRUSTED_ORIGINS'))
    
    def test_middleware_alignment(self):
        """Test that middleware is consistent between settings"""
        from config import simple_settings, production_settings
        
        # Core middleware that should be in both
        core_middleware = [
            'corsheaders.middleware.CorsMiddleware',
            'django.middleware.security.SecurityMiddleware',
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.middleware.common.CommonMiddleware',
            'django.middleware.csrf.CsrfViewMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'django.contrib.messages.middleware.MessageMiddleware',
            'django.middleware.clickjacking.XFrameOptionsMiddleware',
        ]
        
        for middleware in core_middleware:
            self.assertIn(middleware, simple_settings.MIDDLEWARE,
                         f"Middleware {middleware} missing from simple_settings")
            self.assertIn(middleware, production_settings.MIDDLEWARE,
                         f"Middleware {middleware} missing from production_settings")
    
    def test_rest_framework_configuration(self):
        """Test REST Framework configuration alignment"""
        from config import simple_settings, production_settings
        
        # Both should have REST Framework settings
        self.assertTrue(hasattr(simple_settings, 'REST_FRAMEWORK'))
        self.assertTrue(hasattr(production_settings, 'REST_FRAMEWORK'))
        
        # Both should have pagination configured
        self.assertIn('DEFAULT_PAGINATION_CLASS', simple_settings.REST_FRAMEWORK)
        self.assertIn('DEFAULT_PAGINATION_CLASS', production_settings.REST_FRAMEWORK)
        
        # Both should have authentication configured
        self.assertIn('DEFAULT_AUTHENTICATION_CLASSES', simple_settings.REST_FRAMEWORK)
        self.assertIn('DEFAULT_AUTHENTICATION_CLASSES', production_settings.REST_FRAMEWORK)
    
    def test_static_files_configuration(self):
        """Test static files configuration alignment"""
        from config import simple_settings, production_settings
        
        # Both should have static files configuration
        self.assertTrue(hasattr(simple_settings, 'STATIC_URL'))
        self.assertTrue(hasattr(production_settings, 'STATIC_URL'))
        self.assertTrue(hasattr(simple_settings, 'STATIC_ROOT'))
        self.assertTrue(hasattr(production_settings, 'STATIC_ROOT'))
        
        # Both should use WhiteNoise for static files
        self.assertEqual(simple_settings.STATICFILES_STORAGE, 
                        'whitenoise.storage.CompressedManifestStaticFilesStorage')
        self.assertEqual(production_settings.STATICFILES_STORAGE, 
                        'whitenoise.storage.CompressedManifestStaticFilesStorage')
    
    def test_media_files_configuration(self):
        """Test media files configuration alignment"""
        from config import simple_settings, production_settings
        
        # Both should have media files configuration
        self.assertTrue(hasattr(simple_settings, 'MEDIA_URL'))
        self.assertTrue(hasattr(production_settings, 'MEDIA_URL'))
        self.assertTrue(hasattr(simple_settings, 'MEDIA_ROOT'))
        self.assertTrue(hasattr(production_settings, 'MEDIA_ROOT'))
    
    def test_security_settings_alignment(self):
        """Test security settings are consistent"""
        from config import simple_settings, production_settings
        
        # Both should have security settings
        self.assertTrue(hasattr(simple_settings, 'SECRET_KEY'))
        self.assertTrue(hasattr(production_settings, 'SECRET_KEY'))
        self.assertTrue(hasattr(simple_settings, 'DEBUG'))
        self.assertTrue(hasattr(production_settings, 'DEBUG'))
        self.assertTrue(hasattr(simple_settings, 'ALLOWED_HOSTS'))
        self.assertTrue(hasattr(production_settings, 'ALLOWED_HOSTS'))
    
    def test_custom_user_model_alignment(self):
        """Test custom user model configuration"""
        from config import simple_settings, production_settings
        
        # Both should use the same custom user model
        self.assertEqual(simple_settings.AUTH_USER_MODEL, 'users.StaffUser')
        self.assertEqual(production_settings.AUTH_USER_MODEL, 'users.StaffUser')
    
    def test_time_zone_and_language_alignment(self):
        """Test time zone and language settings alignment"""
        from config import simple_settings, production_settings
        
        # Both should have consistent time zone and language settings
        self.assertEqual(simple_settings.LANGUAGE_CODE, production_settings.LANGUAGE_CODE)
        self.assertEqual(simple_settings.TIME_ZONE, production_settings.TIME_ZONE)
        self.assertEqual(simple_settings.USE_I18N, production_settings.USE_I18N)
        self.assertEqual(simple_settings.USE_L10N, production_settings.USE_L10N)
        self.assertEqual(simple_settings.USE_TZ, production_settings.USE_TZ)


class ModelConfigurationTests(TestCase):
    """Test that models are properly configured"""
    
    def test_pitstop_application_time_slots(self):
        """Test that PitStopApplication has the correct time slot choices"""
        from clients.models import PitStopApplication
        
        expected_choices = [
            ('6-12', '6am-12pm'),
            ('13-21', '1pm-9pm'),
            ('22-5', '10pm-5am'),
        ]
        
        self.assertEqual(PitStopApplication.SHIFT_CHOICES, expected_choices)
    
    def test_client_availability_time_slots(self):
        """Test that ClientAvailability has the correct time slot choices"""
        from clients.models_extensions import ClientAvailability
        
        expected_choices = [
            ('6-12', '6am-12pm'),
            ('13-21', '1pm-9pm'),
            ('22-5', '10pm-5am'),
        ]
        
        self.assertEqual(ClientAvailability.TIME_SLOT_CHOICES, expected_choices)
    
    def test_worksite_has_time_slots_field(self):
        """Test that WorkSite has the available_time_slots field"""
        from clients.models_extensions import WorkSite
        
        # Check that the field exists
        self.assertTrue(hasattr(WorkSite, 'available_time_slots'))
        
        # Check that it's a JSONField
        from django.db import models
        field = WorkSite._meta.get_field('available_time_slots')
        self.assertIsInstance(field, models.JSONField)
    
    def test_client_availability_has_preferred_time_slots(self):
        """Test that ClientAvailability has the preferred_time_slots field"""
        from clients.models_extensions import ClientAvailability
        
        # Check that the field exists
        self.assertTrue(hasattr(ClientAvailability, 'preferred_time_slots'))
        
        # Check that it's a JSONField
        from django.db import models
        field = ClientAvailability._meta.get_field('preferred_time_slots')
        self.assertIsInstance(field, models.JSONField)


class StorageConfigurationTests(TestCase):
    """Test storage configuration"""
    
    def test_azure_storage_class_exists(self):
        """Test that AzurePrivateStorage class exists and is properly configured"""
        try:
            from clients.storage import AzurePrivateStorage
            self.assertTrue(hasattr(AzurePrivateStorage, 'account_name'))
            self.assertTrue(hasattr(AzurePrivateStorage, 'azure_container'))
        except ImportError as e:
            self.fail(f"Failed to import AzurePrivateStorage: {e}")
    
    def test_azure_storage_functions_exist(self):
        """Test that Azure storage utility functions exist"""
        try:
            from clients.storage import generate_document_sas_url, get_azure_container_client
            self.assertTrue(callable(generate_document_sas_url))
            self.assertTrue(callable(get_azure_container_client))
        except ImportError as e:
            self.fail(f"Failed to import Azure storage functions: {e}")
    
    def test_document_model_has_proper_fields(self):
        """Test that Document model has proper fields for blob storage"""
        from clients.models import Document
        
        # Check that file field exists
        self.assertTrue(hasattr(Document, 'file'))
        
        # Check that metadata fields exist
        self.assertTrue(hasattr(Document, 'file_size'))
        self.assertTrue(hasattr(Document, 'content_type'))
        self.assertTrue(hasattr(Document, 'uploaded_by'))
        
        # Check that download_url property exists
        self.assertTrue(hasattr(Document, 'download_url'))
        self.assertTrue(callable(getattr(Document, 'download_url', None)))


if __name__ == '__main__':
    # Run tests directly
    import django
    from django.conf import settings
    from django.test.utils import get_runner
    
    if not settings.configured:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.simple_settings')
        django.setup()
    
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(['config.test_config_alignment'])
    
    if failures:
        sys.exit(1)
