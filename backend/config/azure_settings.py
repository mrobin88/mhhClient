"""
Azure Production Settings for Mission Hiring Hall Client System
"""

import os
from .settings import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Azure-specific settings
ALLOWED_HOSTS = [
    'mhh-client-backend-cuambzgeg3dfbphd.centralus-01.azurewebsites.net',
    'localhost',
    '127.0.0.1'
]

# Add any additional allowed hosts from environment
if os.getenv('ALLOWED_HOSTS'):
    ALLOWED_HOSTS.extend(os.getenv('ALLOWED_HOSTS').split(','))

# Database - Azure PostgreSQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DATABASE_NAME', 'mhh_client_db'),
        'USER': os.getenv('DATABASE_USER', 'mhhsupport'),
        'PASSWORD': os.getenv('DATABASE_PASSWORD'),
        'HOST': os.getenv('DATABASE_HOST', 'mhh-client-postgres.postgres.database.azure.com'),
        'PORT': os.getenv('DATABASE_PORT', '5432'),
        'OPTIONS': {
            'sslmode': 'require',
        },
    }
}

# CORS settings for Azure Static Web App
CORS_ALLOWED_ORIGINS = [
    "https://brave-mud-077eb1810.1.azurestaticapps.net",
    "http://localhost:3000",
    "http://localhost:5173",
]

# Add CORS origins from environment if provided
if os.getenv('CORS_ALLOWED_ORIGINS'):
    CORS_ALLOWED_ORIGINS.extend(os.getenv('CORS_ALLOWED_ORIGINS').split(','))

CORS_ALLOW_CREDENTIALS = True

# Security settings for production
SECURE_SSL_REDIRECT = False  # Disabled to prevent redirect loops
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Static files configuration for Azure
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'

# Use WhiteNoise for static file serving
MIDDLEWARE = [
    'whitenoise.middleware.WhiteNoiseMiddleware',
] + MIDDLEWARE

# WhiteNoise configuration
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': '/tmp/django.log',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Azure Application Insights (optional)
if os.getenv('APPLICATIONINSIGHTS_CONNECTION_STRING'):
    INSTALLED_APPS += ['opencensus.ext.django']
    MIDDLEWARE = [
        'opencensus.ext.django.middleware.OpencensusMiddleware',
    ] + MIDDLEWARE
    
    OPENCENSUS = {
        'TRACE': {
            'SAMPLER': 'opencensus.trace.samplers.ProbabilitySampler(rate=1.0)',
        },
    }
