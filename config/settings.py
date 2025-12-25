"""
Unified Django Settings
Automatically detects Azure environment and uses environment variables for all sensitive configuration.
"""

import os
import sys
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Detect if running in Azure App Service
# WEBSITE_HOSTNAME is set by Azure App Service
IS_AZURE = bool(os.getenv('WEBSITE_HOSTNAME'))

# SECURITY WARNING: keep the secret key used in production secret!
# MUST be set via environment variable in production
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    if IS_AZURE:
        raise ValueError("SECRET_KEY environment variable must be set in Azure App Service")
    else:
        SECRET_KEY = 'django-insecure-fallback-key-change-in-production'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# Allowed hosts - automatically include Azure hostname if present
ALLOWED_HOSTS = []
if IS_AZURE:
    # Azure automatically sets WEBSITE_HOSTNAME
    website_hostname = os.getenv('WEBSITE_HOSTNAME')
    if website_hostname:
        ALLOWED_HOSTS.append(website_hostname)
    # Azure internal IP
    ALLOWED_HOSTS.append('169.254.130.2')

# Add localhost for development
if DEBUG or not IS_AZURE:
    ALLOWED_HOSTS.extend(['localhost', '127.0.0.1'])

# Add any additional allowed hosts from environment
if os.getenv('ALLOWED_HOSTS'):
    ALLOWED_HOSTS.extend([h.strip() for h in os.getenv('ALLOWED_HOSTS').split(',') if h.strip()])

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
    'corsheaders',
    'storages',  # Django-storages for Azure Blob Storage
    'users.apps.UsersConfig',
    'clients',
]

# Custom user model
AUTH_USER_MODEL = 'users.StaffUser'

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'config.middleware.RequestLoggingMiddleware',  # Request logging for Azure
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Azure Application Insights (optional) - add middleware if configured
if os.getenv('APPLICATIONINSIGHTS_CONNECTION_STRING'):
    try:
        INSTALLED_APPS.append('opencensus.ext.django')
        MIDDLEWARE.insert(0, 'opencensus.ext.django.middleware.OpencensusMiddleware')
    except ImportError:
        pass  # opencensus not installed

# CORS configuration
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    # Get CORS origins from environment
    cors_origins = os.getenv('CORS_ALLOWED_ORIGINS', '')
    CORS_ALLOWED_ORIGINS = [o.strip() for o in cors_origins.split(',') if o.strip()]
    # Accept all Azure Static Web Apps subdomains
    CORS_ALLOWED_ORIGIN_REGEXES = [
        r"^https://.*\.azurestaticapps\.net$",
        r"^https://.*\.azurewebsites\.net$",
    ]
    CORS_ALLOW_CREDENTIALS = True
    CORS_ALLOW_HEADERS = [
        'accept', 'accept-encoding', 'authorization', 'content-type', 
        'dnt', 'origin', 'user-agent', 'x-csrftoken', 'x-requested-with'
    ]

# CSRF trusted origins
csrf_origins = os.getenv('CSRF_TRUSTED_ORIGINS', '')
if csrf_origins:
    CSRF_TRUSTED_ORIGINS = [o.strip() for o in csrf_origins.split(',') if o.strip()]
else:
    # Defaults suitable for Azure deployment
    CSRF_TRUSTED_ORIGINS = []
    if IS_AZURE and os.getenv('WEBSITE_HOSTNAME'):
        CSRF_TRUSTED_ORIGINS.append(f'https://{os.getenv("WEBSITE_HOSTNAME")}')
    CSRF_TRUSTED_ORIGINS.append('https://*.azurestaticapps.net')

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

# Database configuration - all sensitive values from environment
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    # Parse DATABASE_URL format
    import urllib.parse as urlparse
    url = urlparse.urlparse(DATABASE_URL)
    host = url.hostname or ''
    # Decide SSL mode: disable for localhost, require otherwise
    default_sslmode = 'disable' if host in ('localhost', '127.0.0.1') else 'require'
    sslmode = os.getenv('DATABASE_SSLMODE', default_sslmode)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': url.path[1:],  # Remove leading '/'
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
    host = os.getenv('DATABASE_HOST', '')
    if not host:
        raise ValueError("DATABASE_HOST must be set when using DATABASE_PASSWORD")
    
    default_sslmode = 'disable' if host in ('localhost', '127.0.0.1') else 'require'
    sslmode = os.getenv('DATABASE_SSLMODE', default_sslmode)
    
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DATABASE_NAME', ''),
            'USER': os.getenv('DATABASE_USER', ''),
            'PASSWORD': os.getenv('DATABASE_PASSWORD'),  # Required
            'HOST': host,
            'PORT': os.getenv('DATABASE_PORT', '5432'),
            'OPTIONS': {
                'sslmode': sslmode,
            },
        }
    }
    # Validate required fields
    if not DATABASES['default']['NAME']:
        raise ValueError("DATABASE_NAME must be set")
    if not DATABASES['default']['USER']:
        raise ValueError("DATABASE_USER must be set")
else:
    # Fallback to SQLite for local development only
    if IS_AZURE:
        raise ValueError("Database configuration required in Azure. Set DATABASE_URL or DATABASE_PASSWORD")
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
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
STATICFILES_DIRS = [BASE_DIR / "static"]

# Media files - Azure Blob Storage for production, local for dev
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Azure Blob Storage configuration - all sensitive values from environment
AZURE_ACCOUNT_NAME = os.getenv('AZURE_ACCOUNT_NAME')
AZURE_ACCOUNT_KEY = os.getenv('AZURE_ACCOUNT_KEY')
AZURE_CONTAINER = os.getenv('AZURE_CONTAINER', 'client-docs')

if AZURE_ACCOUNT_NAME and AZURE_ACCOUNT_KEY:
    # Use Azure Blob Storage for file uploads
    DEFAULT_FILE_STORAGE = 'clients.storage.AzurePrivateStorage'
    AZURE_CUSTOM_DOMAIN = f'{AZURE_ACCOUNT_NAME}.blob.core.windows.net'
    if AZURE_CONTAINER:
        MEDIA_URL = f'https://{AZURE_ACCOUNT_NAME}.blob.core.windows.net/{AZURE_CONTAINER}/'
else:
    # Fallback to local file storage for development
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Email configuration - all sensitive values from environment
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
if IS_AZURE and os.getenv('WEBSITE_HOSTNAME'):
    ADMIN_BASE_URL = os.getenv('ADMIN_BASE_URL', f'https://{os.getenv("WEBSITE_HOSTNAME")}')
else:
    ADMIN_BASE_URL = os.getenv('ADMIN_BASE_URL', 'http://localhost:8000')

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

# Production security settings
if not DEBUG:
    SECURE_SSL_REDIRECT = False  # Azure handles SSL termination
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# Logging configuration - outputs to stdout for Azure Log Stream
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'stream': sys.stdout,  # Explicitly use stdout for Azure Log Stream
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.contrib.admin': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.contrib.auth': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'WARNING',  # Only log warnings/errors for DB
            'propagate': False,
        },
        'users': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'clients': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Cache configuration (optional but recommended for production)
if os.getenv('REDIS_URL'):
    try:
        CACHES = {
            'default': {
                'BACKEND': 'django_redis.cache.RedisCache',
                'LOCATION': os.getenv('REDIS_URL'),
                'OPTIONS': {
                    'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                }
            }
        }
        SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
        SESSION_CACHE_ALIAS = 'default'
    except ImportError:
        pass  # django-redis not installed

# Admin site customization moved to users.apps.UsersConfig.ready() to avoid AppRegistryNotReady

