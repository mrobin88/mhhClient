"""
Compatibility layer for config.settings
This file imports everything from simple_settings.py to maintain compatibility
with Azure App Service environment variable: DJANGO_SETTINGS_MODULE=config.settings

Both config.settings and config.simple_settings will work identically.
"""

# Import all settings from simple_settings
from .simple_settings import *

