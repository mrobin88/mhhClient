"""Pacific (PitStop) display timezone helpers — DB stays UTC when USE_TZ=True."""
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import timezone


def display_tz():
    return ZoneInfo(settings.TIME_ZONE)


def to_display_tz(dt):
    if not dt:
        return None
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt.astimezone(display_tz())


def format_display_datetime(dt, fmt='%b %d, %Y %I:%M %p'):
    localized = to_display_tz(dt)
    return localized.strftime(fmt) if localized else ''
