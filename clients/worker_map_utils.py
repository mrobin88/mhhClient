"""Static map snapshots for worker clock in/out (no geofence validation)."""
import logging
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)

OSM_STATIC_MAP_URL = 'https://staticmap.openstreetmap.de/staticmap.php'


def fetch_static_map_image(latitude, longitude, *, width=400, height=200, zoom=16):
    """Download a small OSM static map PNG for approximate location reference."""
    try:
        lat = float(latitude)
        lng = float(longitude)
    except (TypeError, ValueError):
        return None

    params = urlencode({
        'center': f'{lat},{lng}',
        'zoom': str(zoom),
        'size': f'{width}x{height}',
        'markers': f'{lat},{lng}',
    })
    url = f'{OSM_STATIC_MAP_URL}?{params}'
    request = Request(url, headers={'User-Agent': 'mhhClient-worker-clock/1.0'})
    try:
        with urlopen(request, timeout=8) as response:
            if response.status != 200:
                return None
            data = response.read()
            if not data:
                return None
            return ContentFile(data, name='map_snapshot.png')
    except Exception as exc:
        logger.warning('Static map fetch failed: %s', exc)
        return None
