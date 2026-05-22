"""
Worker Portal API — focused on worker clock in/out with geolocation.
"""
import json
import math
from datetime import datetime, timedelta, timezone as dt_timezone

from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.decorators import api_view, authentication_classes, parser_classes, permission_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models_extensions import (
    WorkerAccount,
    WorkerSessionToken,
    WorkSite,
    WorkerTimePunch,
)
from .serializers import (
    WorkerLoginSerializer,
    WorkerAccountSerializer,
    WorkSiteSerializer,
    WorkerTimePunchSerializer,
)

class WorkerSession:
    """DB-backed worker portal session (multi-process safe)."""

    @classmethod
    def create_session(cls, worker_account):
        import uuid

        token = str(uuid.uuid4())
        expires_at = timezone.now() + timedelta(days=7)
        WorkerSessionToken.objects.create(
            token=token,
            worker_account=worker_account,
            expires_at=expires_at,
        )
        return token

    @classmethod
    def get_session(cls, token):
        if not token:
            return None
        try:
            session = WorkerSessionToken.objects.select_related(
                'worker_account', 'worker_account__client'
            ).get(
                token=token,
                expires_at__gt=timezone.now(),
            )
            return {
                'worker_account_id': session.worker_account_id,
                'client_id': session.worker_account.client_id,
                'created_at': session.created_at,
            }
        except WorkerSessionToken.DoesNotExist:
            return None

    @classmethod
    def delete_session(cls, token):
        if not token:
            return
        WorkerSessionToken.objects.filter(token=token).delete()


def _worker_token(request):
    return (request.headers.get('Authorization') or '').replace('Token ', '').strip()


def _require_worker(request):
    session = WorkerSession.get_session(_worker_token(request))
    if not session:
        return None, Response(
            {'error': 'Invalid or expired session'},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    try:
        account = WorkerAccount.objects.select_related('client').get(
            id=session['worker_account_id']
        )
    except WorkerAccount.DoesNotExist:
        return None, Response(
            {'error': 'Worker account not found'},
            status=status.HTTP_404_NOT_FOUND,
        )
    if not account.is_active:
        return None, Response(
            {'error': 'Portal access is turned off'},
            status=status.HTTP_403_FORBIDDEN,
        )
    return account, None


def _parse_client_timestamp(value):
    if not value:
        return None
    dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone=dt_timezone.utc)
    return dt


def _parse_geo_payload(geo):
    default = {
        'status': WorkerTimePunch.GEO_STATUS_SKIPPED,
        'error': '',
        'latitude': None,
        'longitude': None,
        'accuracy': None,
        'client_reported_at': None,
    }
    if isinstance(geo, str):
        try:
            geo = json.loads(geo)
        except json.JSONDecodeError:
            geo = {'status': WorkerTimePunch.GEO_STATUS_ERROR, 'error': 'Invalid geolocation payload'}
    if not isinstance(geo, dict):
        return default

    status_value = str(geo.get('status') or WorkerTimePunch.GEO_STATUS_SKIPPED).strip().lower()
    allowed = {choice[0] for choice in WorkerTimePunch.GEO_STATUS_CHOICES}
    default['status'] = status_value if status_value in allowed else WorkerTimePunch.GEO_STATUS_ERROR
    default['error'] = str(geo.get('error') or '')[:200]

    try:
        lat = geo.get('latitude')
        lng = geo.get('longitude')
        acc = geo.get('accuracy')
        default['latitude'] = None if lat is None else float(lat)
        default['longitude'] = None if lng is None else float(lng)
        default['accuracy'] = None if acc is None else float(acc)
    except (TypeError, ValueError):
        default['status'] = WorkerTimePunch.GEO_STATUS_ERROR
        if not default['error']:
            default['error'] = 'Invalid geolocation payload'
        default['latitude'] = None
        default['longitude'] = None
        default['accuracy'] = None

    try:
        default['client_reported_at'] = _parse_client_timestamp(geo.get('timestamp'))
    except Exception:
        default['client_reported_at'] = None

    return default


def _basic_geo_validation(geo_payload):
    """
    Lightweight checks to flag obviously bad/suspicious location payloads.
    """
    status_value = geo_payload.get('status')
    if status_value != WorkerTimePunch.GEO_STATUS_CAPTURED:
        return False, f"No captured location ({status_value})"

    lat = geo_payload.get('latitude')
    lng = geo_payload.get('longitude')
    acc = geo_payload.get('accuracy')

    if lat is None or lng is None:
        return False, 'Missing latitude/longitude'
    if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
        return False, 'Latitude/longitude out of range'
    if abs(lat) < 0.0001 and abs(lng) < 0.0001:
        return False, 'Coordinate is near 0,0'
    if acc is None:
        return False, 'Missing GPS accuracy value'
    if acc > 500:
        return False, f'Low precision ({acc:.0f}m)'
    return True, f'Captured with accuracy {acc:.0f}m'


def _distance_meters(lat1, lon1, lat2, lon2):
    radius = 6371000.0
    lat1_r, lon1_r = math.radians(lat1), math.radians(lon1)
    lat2_r, lon2_r = math.radians(lat2), math.radians(lon2)
    d_lat = lat2_r - lat1_r
    d_lon = lon2_r - lon1_r
    a = math.sin(d_lat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(d_lon / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def _site_geo_validation(site, geo_payload):
    if not site:
        return False, 'Select a PitStop location first', None
    if site.latitude is None or site.longitude is None:
        return False, 'Site geolocation is not configured. Ask staff to set site coordinates.', None
    if geo_payload.get('status') != WorkerTimePunch.GEO_STATUS_CAPTURED:
        return False, f'No captured location ({geo_payload.get("status")})', None
    if geo_payload.get('latitude') is None or geo_payload.get('longitude') is None:
        return False, 'Missing worker location coordinates', None
    distance = _distance_meters(
        float(geo_payload['latitude']),
        float(geo_payload['longitude']),
        float(site.latitude),
        float(site.longitude),
    )
    max_distance = int(getattr(settings, 'WORKER_CLOCK_GEOFENCE_METERS', 250))
    if distance > max_distance:
        return False, f'Outside site geofence ({distance:.0f}m > {max_distance}m)', distance
    return True, f'Within geofence ({distance:.0f}m)', distance


def _punch_work_site(work_site_id):
    if not work_site_id:
        return None, Response(
            {'work_site_id': ['Choose your PitStop location.']},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        site = WorkSite.objects.get(pk=work_site_id, is_active=True)
    except (TypeError, ValueError, WorkSite.DoesNotExist):
        return None, Response(
            {'error': 'PitStop location not found.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return site, None


@api_view(['POST'])
@permission_classes([AllowAny])
def worker_login(request):
    serializer = WorkerLoginSerializer(data=request.data)
    if serializer.is_valid():
        worker_account = serializer.validated_data['worker_account']
        token = WorkerSession.create_session(worker_account)
        return Response(
            {
                'token': token,
                'worker_account': WorkerAccountSerializer(worker_account).data,
                'message': 'Login successful',
            },
            status=status.HTTP_200_OK,
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def worker_logout(request):
    WorkerSession.delete_session(_worker_token(request))
    return Response({'message': 'Logged out successfully'})


@api_view(['GET'])
@permission_classes([AllowAny])
def worker_profile(request):
    worker_account, err = _require_worker(request)
    if err:
        return err
    return Response(WorkerAccountSerializer(worker_account).data)


@api_view(['GET'])
@permission_classes([AllowAny])
def worker_assignments(request):
    return Response(
        {'error': 'Assignments are disabled. Use /api/worker/work-sites/ and /api/worker/time-punch/.'},
        status=status.HTTP_410_GONE,
    )


@api_view(['GET'])
@permission_classes([AllowAny])
def worker_work_sites(request):
    """Active PitStop sites used by iPads for clock in/out geolocation validation."""
    _, err = _require_worker(request)
    if err:
        return err
    sites = WorkSite.objects.filter(is_active=True, site_type='pitstop').order_by('name')
    return Response(WorkSiteSerializer(sites, many=True).data)


@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
@permission_classes([AllowAny])
def worker_shift_proof(request):
    """Deprecated endpoint retained for old clients."""
    account, err = _require_worker(request)
    if err:
        return err

    return Response(
        {'error': 'Photo check-in is disabled. Use clock in/out with location.'},
        status=status.HTTP_410_GONE,
    )


@api_view(['GET', 'PATCH'])
@permission_classes([AllowAny])
def worker_availability(request):
    """Simple Available / Not Available toggle."""
    account, err = _require_worker(request)
    if err:
        return err

    if request.method == 'GET':
        return Response({'is_available': account.is_available})

    account.is_available = bool(request.data.get('is_available'))
    account.save(update_fields=['is_available', 'is_approved'])
    return Response({'is_available': account.is_available})


@api_view(['GET'])
@permission_classes([AllowAny])
def worker_open_shifts(request):
    return Response(
        {'error': 'Open shifts are disabled for the iPad clock flow.'},
        status=status.HTTP_410_GONE,
    )


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def worker_shift_interests(request):
    return Response(
        {'error': 'Shift interests are disabled for the iPad clock flow.'},
        status=status.HTTP_410_GONE,
    )


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def worker_time_punch(request):
    """Worker clock in/out with geolocation validated against selected PitStop site."""
    account, err = _require_worker(request)
    if err:
        return err

    if request.method == 'GET':
        punches = (
            WorkerTimePunch.objects.filter(worker_account=account)
            .select_related('work_site', 'assignment', 'assignment__work_site')
            .order_by('-clock_in_at')[:25]
        )
        open_punch = next((p for p in punches if p.clock_out_at is None), None)
        return Response(
            {
                'active_punch': WorkerTimePunchSerializer(open_punch).data if open_punch else None,
                'punches': WorkerTimePunchSerializer(punches, many=True).data,
            }
        )

    action = str(request.data.get('action') or '').strip().lower()
    if action not in {'clock_in', 'clock_out'}:
        return Response(
            {'action': ['Use "clock_in" or "clock_out".']},
            status=status.HTTP_400_BAD_REQUEST,
        )

    site, site_err = _punch_work_site(request.data.get('work_site_id'))
    if site_err:
        return site_err

    geo = _parse_geo_payload(request.data.get('geolocation'))
    geo_basic_ok, geo_basic_note, _geo_distance = _site_geo_validation(site, geo)
    now = timezone.now()

    open_punch = (
        WorkerTimePunch.objects.filter(worker_account=account, clock_out_at__isnull=True)
        .select_related('work_site', 'assignment', 'assignment__work_site')
        .order_by('-clock_in_at')
        .first()
    )

    if action == 'clock_in':
        if open_punch:
            return Response(
                {
                    'error': 'You are already clocked in. Clock out first.',
                    'active_punch': WorkerTimePunchSerializer(open_punch).data,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        punch = WorkerTimePunch.objects.create(
            worker_account=account,
            work_site=site,
            clock_in_at=now,
            clock_in_client_reported_at=geo['client_reported_at'],
            clock_in_latitude=geo['latitude'],
            clock_in_longitude=geo['longitude'],
            clock_in_accuracy_meters=geo['accuracy'],
            clock_in_geo_status=geo['status'],
            clock_in_geo_error=geo['error'],
            clock_in_geo_basic_ok=geo_basic_ok,
            clock_in_geo_basic_note=geo_basic_note,
        )
        return Response(
            {
                'message': f'Clocked in at {site.name}.',
                'punch': WorkerTimePunchSerializer(punch).data,
            },
            status=status.HTTP_201_CREATED,
        )

    if not open_punch:
        return Response(
            {'error': 'No active clock-in found.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    open_punch.clock_out_at = now
    open_punch.clock_out_server_received_at = now
    open_punch.clock_out_client_reported_at = geo['client_reported_at']
    open_punch.clock_out_latitude = geo['latitude']
    open_punch.clock_out_longitude = geo['longitude']
    open_punch.clock_out_accuracy_meters = geo['accuracy']
    open_punch.clock_out_geo_status = geo['status']
    open_punch.clock_out_geo_error = geo['error']
    open_punch.clock_out_geo_basic_ok = geo_basic_ok
    open_punch.clock_out_geo_basic_note = geo_basic_note
    open_punch.save(
        update_fields=[
            'clock_out_at',
            'clock_out_server_received_at',
            'clock_out_client_reported_at',
            'clock_out_latitude',
            'clock_out_longitude',
            'clock_out_accuracy_meters',
            'clock_out_geo_status',
            'clock_out_geo_error',
            'clock_out_geo_basic_ok',
            'clock_out_geo_basic_note',
        ]
    )
    return Response(
        {
            'message': f'Clocked out from {open_punch.work_site.name if open_punch.work_site else "site"}.',
            'punch': WorkerTimePunchSerializer(open_punch).data,
        }
    )


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def worker_notes(request):
    return Response(
        {'error': 'Worker notes are disabled for the iPad clock flow.'},
        status=status.HTTP_410_GONE,
    )


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def worker_time_off_requests(request):
    return Response(
        {'error': 'Time-off requests are disabled for the iPad clock flow.'},
        status=status.HTTP_410_GONE,
    )


@api_view(['PATCH'])
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def staff_shift_interest_update(request, pk):
    return Response(
        {'error': 'Shift interest workflows are disabled.'},
        status=status.HTTP_410_GONE,
    )
