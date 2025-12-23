"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/howto/deployment/wsgi/
"""

import os
import sys
import traceback
import logging

# Set up logging before Django initialization
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s %(asctime)s %(module)s %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.simple_settings')

try:
    from django.core.wsgi import get_wsgi_application
    application = get_wsgi_application()
    logger.info("WSGI application initialized successfully")
except Exception as e:
    # Log full stack trace for container start failures
    logger.error(f"Failed to initialize WSGI application: {e}")
    logger.error(f"Full traceback:\n{traceback.format_exc()}")
    # Re-raise to prevent silent failures
    raise
