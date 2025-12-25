"""
Simple Django settings without django-environ dependency
"""

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-fallback-key-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,169.254.130.2,mhh-client-backend-cuambzgeg3dfbphd.centralus-01.azurewebsites.net').split(',')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'django_filters',
    'users.apps.UsersConfig',
    'clients',
    'corsheaders',
    'storages',  # Django-storages for Azure Blob Storage
]

# Custom user model
AUTH_USER_MODEL = 'users.StaffUser'

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# CORS configuration
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    cors_origins = os.getenv('CORS_ALLOWED_ORIGINS', '')
    CORS_ALLOWED_ORIGINS = cors_origins.split(',') if cors_origins else []
    # Accept all Azure Static Web Apps subdomains (e.g., with/without shard like .1.)
    CORS_ALLOWED_ORIGIN_REGEXES = [
        r"^https://.*\\.azurestaticapps\\.net$",
        r"^https://.*\\.azurewebsites\\.net$",
    ]
    CORS_ALLOW_CREDENTIALS = True
    CORS_ALLOW_HEADERS = list(set([
        'accept', 'accept-encoding', 'authorization', 'content-type', 'dnt', 'origin', 'user-agent', 'x-csrftoken', 'x-requested-with'
    ]))

# CSRF trusted origins (comma-separated list in env)
csrf_origins = os.getenv('CSRF_TRUSTED_ORIGINS', '')
if csrf_origins:
    CSRF_TRUSTED_ORIGINS = [o.strip() for o in csrf_origins.split(',') if o.strip()]
else:
    # Defaults suitable for production deployment
    CSRF_TRUSTED_ORIGINS = [
        'https://mhh-client-backend-cuambzgeg3dfbphd.centralus-01.azurewebsites.net',
        'https://*.azurestaticapps.net',
    ]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    # Parse DATABASE_URL
    import urllib.parse as urlparse
    url = urlparse.urlparse(DATABASE_URL)
    host = url.hostname or ''
    # Decide SSL mode: disable for localhost, require otherwise; allow override via env
    default_sslmode = 'disable' if host in ('localhost', '127.0.0.1') else 'require'
    sslmode = os.getenv('DATABASE_SSLMODE', default_sslmode)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': url.path[1:],
            'USER': url.username,
            'PASSWORD': url.password,
            'HOST': url.hostname,
            'PORT': url.port or 5432,
            'OPTIONS': {
                'sslmode': sslmode,
            },
        }
    }
elif os.getenv('DATABASE_PASSWORD'):
    # Use PostgreSQL with individual environment variables
    host = os.getenv('DATABASE_HOST', 'mhh-client-postgres.postgres.database.azure.com')
    default_sslmode = 'disable' if host in ('localhost', '127.0.0.1') else 'require'
    sslmode = os.getenv('DATABASE_SSLMODE', default_sslmode)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DATABASE_NAME', 'mhh_client_db'),
            'USER': os.getenv('DATABASE_USER', 'mhhsupport'),
            'PASSWORD': os.getenv('DATABASE_PASSWORD'),
            'HOST': host,
            'PORT': os.getenv('DATABASE_PORT', '5432'),
            'OPTIONS': {
                'sslmode': sslmode,
            },
        }
    }
else:
    # Fallback to SQLite for local testing
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
# Use non-manifest storage for development to avoid missing manifest errors
# For production, ensure collectstatic is run during deployment
if os.getenv('DEBUG', 'False').lower() == 'true':
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'
else:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files - Azure Blob Storage for production, local for dev
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Azure Blob Storage configuration for file uploads
if os.getenv('AZURE_ACCOUNT_NAME') and os.getenv('AZURE_ACCOUNT_KEY'):
    # Use Azure Blob Storage for file uploads in production
    DEFAULT_FILE_STORAGE = 'clients.storage.AzurePrivateStorage'
    
    # Azure Storage settings
    AZURE_ACCOUNT_NAME = os.getenv('AZURE_ACCOUNT_NAME')
    AZURE_ACCOUNT_KEY = os.getenv('AZURE_ACCOUNT_KEY')
    AZURE_CONTAINER = os.getenv('AZURE_CONTAINER', 'client-docs')
    AZURE_CUSTOM_DOMAIN = f'{AZURE_ACCOUNT_NAME}.blob.core.windows.net'
else:
    # Fallback to local file storage for development
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Email configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER or 'noreply@missionhiringhall.org')
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# Case note alert email (fallback if staff member email not found)
CASE_NOTE_ALERT_EMAIL = os.getenv('CASE_NOTE_ALERT_EMAIL', None)

# Admin base URL for email links
ADMIN_BASE_URL = os.getenv('ADMIN_BASE_URL', 'https://mhh-client-backend-cuambzgeg3dfbphd.centralus-01.azurewebsites.net')

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
}

# Admin site customization moved to users.apps.UsersConfig.ready() to avoid AppRegistryNotReady
