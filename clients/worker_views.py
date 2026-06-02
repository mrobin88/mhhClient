"""
Worker Portal API — focused on worker clock in/out with geolocation.
"""
import json
import math
from datetime import datetime, timedelta, timezone as dt_timezone
from django.conf import settings
from django.db.models import DurationField, ExpressionWrapper, F, Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    parser_classes,
    permission_classes,
    throttle_classes,
)
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
from .throttles import WorkerPunchThrottle
from .time_display import display_tz

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


def _distance_meters(lat1, lon1, lat2, lon2):
    radius = 6371000.0
    lat1_r, lon1_r = math.radians(lat1), math.radians(lon1)
    lat2_r, lon2_r = math.radians(lat2), math.radians(lon2)
    d_lat = lat2_r - lat1_r
    d_lon = lon2_r - lon1_r
    a = math.sin(d_lat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(d_lon / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def _pitstop_sites_with_coordinates():
    return WorkSite.objects.filter(
        is_active=True,
        site_type='pitstop',
        latitude__isnull=False,
        longitude__isnull=False,
    )


def _pitstop_geofence_validation(geo_payload, preferred_site=None):
    """Match worker GPS to any active PitStop within the geofence radius.

    Returns (matched_site, ok, note, distance_meters). matched_site is the
    nearest in-range site; preferred_site is used when it is also in range.
    """
    if geo_payload.get('status') != WorkerTimePunch.GEO_STATUS_CAPTURED:
        return None, False, f'No captured location ({geo_payload.get("status")})', None
    if geo_payload.get('latitude') is None or geo_payload.get('longitude') is None:
        return None, False, 'Missing worker location coordinates', None

    sites = list(_pitstop_sites_with_coordinates())
    if not sites:
        return preferred_site, False, 'No PitStop sites have GPS coordinates configured.', None

    lat = float(geo_payload['latitude'])
    lng = float(geo_payload['longitude'])
    max_distance = int(getattr(settings, 'WORKER_CLOCK_GEOFENCE_METERS', 183))

    in_range = []
    nearest_site = None
    nearest_distance = None
    for site in sites:
        distance = _distance_meters(lat, lng, float(site.latitude), float(site.longitude))
        if nearest_distance is None or distance < nearest_distance:
            nearest_distance = distance
            nearest_site = site
        if distance <= max_distance:
            in_range.append((distance, site))

    if not in_range:
        label = nearest_site.name if nearest_site else 'site'
        return (
            preferred_site,
            False,
            f'Outside all PitStop geofences (nearest {label} {nearest_distance:.0f}m > {max_distance}m)',
            nearest_distance,
        )

    in_range.sort(key=lambda item: item[0])
    matched_site = in_range[0][1]
    matched_distance = in_range[0][0]
    if preferred_site:
        for distance, site in in_range:
            if site.pk == preferred_site.pk:
                matched_site = site
                matched_distance = distance
                break

    return (
        matched_site,
        True,
        f'Within geofence at {matched_site.name} ({matched_distance:.0f}m)',
        matched_distance,
    )


WORKER_LOCAL_TZ = display_tz()


def _local_day_bounds(now=None):
    """Return (start_of_today, start_of_tomorrow) anchored to the worker portal's
    display timezone, returned as timezone-aware datetimes (still UTC-comparable).

    The DB stores everything in UTC, but workers see their day in local time.
    """
    now = now or timezone.now()
    local_now = now.astimezone(WORKER_LOCAL_TZ)
    start_today = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_tomorrow = start_today + timedelta(days=1)
    return start_today, start_tomorrow


def _completed_hours_in_range(account, start_dt, end_dt):
    """Net paid hours for completed punches in [start_dt, end_dt) for this worker.

    Net = worked time minus the unpaid lunch. Two SQL aggregates (gross worked
    and total lunch), subtracted in Python — keeps it DB-agnostic and avoids
    nested null-duration arithmetic. Open punches are excluded; the frontend
    adds the live in-progress duration on top of these completed totals.
    """
    aggregates = (
        WorkerTimePunch.objects.filter(
            worker_account=account,
            clock_in_at__gte=start_dt,
            clock_in_at__lt=end_dt,
            clock_out_at__isnull=False,
        )
        .aggregate(
            worked=Sum(
                ExpressionWrapper(
                    F('clock_out_at') - F('clock_in_at'),
                    output_field=DurationField(),
                )
            ),
            lunch=Sum(
                ExpressionWrapper(
                    F('lunch_end_at') - F('lunch_start_at'),
                    output_field=DurationField(),
                )
            ),
        )
    )
    worked = aggregates['worked']
    lunch = aggregates['lunch']
    worked_seconds = worked.total_seconds() if worked else 0
    lunch_seconds = lunch.total_seconds() if lunch else 0
    net_seconds = max(worked_seconds - lunch_seconds, 0)
    return round(net_seconds / 3600, 2)


def _resolve_optional_work_site(work_site_id):
    """Look up an optional WorkSite.

    Worker assignments are still scheduled manually, so the worker app doesn't
    pick a site at punch time. We keep the FK for backward compatibility — if
    a caller (e.g. an older client or staff tooling) provides a site id, we
    honor it. Missing id is fine; an unknown id is a soft error.
    """
    if not work_site_id:
        return None, None
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


def _handle_lunch_action(action, open_punch, geo, now):
    """Start or end the single unpaid lunch break on the worker's open punch."""
    if not open_punch:
        return Response(
            {'error': 'Clock in before starting lunch.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if action == 'start_lunch':
        if open_punch.lunch_start_at is not None:
            return Response(
                {
                    'error': 'Lunch already recorded for this shift.',
                    'active_punch': WorkerTimePunchSerializer(open_punch).data,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        open_punch.lunch_start_at = now
        open_punch.lunch_start_latitude = geo['latitude']
        open_punch.lunch_start_longitude = geo['longitude']
        open_punch.save(
            update_fields=[
                'lunch_start_at',
                'lunch_start_latitude',
                'lunch_start_longitude',
            ]
        )
        return Response(
            {
                'message': 'Lunch started.',
                'punch': WorkerTimePunchSerializer(open_punch).data,
            }
        )

    # end_lunch
    if open_punch.lunch_start_at is None:
        return Response(
            {'error': 'Start lunch before ending it.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if open_punch.lunch_end_at is not None:
        return Response(
            {
                'error': 'Lunch already ended.',
                'active_punch': WorkerTimePunchSerializer(open_punch).data,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    open_punch.lunch_end_at = now
    open_punch.lunch_end_latitude = geo['latitude']
    open_punch.lunch_end_longitude = geo['longitude']
    open_punch.save(
        update_fields=[
            'lunch_end_at',
            'lunch_end_latitude',
            'lunch_end_longitude',
        ]
    )
    return Response(
        {
            'message': f'Lunch ended ({open_punch.lunch_minutes} min).',
            'punch': WorkerTimePunchSerializer(open_punch).data,
        }
    )


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
@throttle_classes([WorkerPunchThrottle])
def worker_time_punch(request):
    """Worker clock in/out with geolocation validated against any active PitStop site."""
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

        today_start, tomorrow_start = _local_day_bounds()
        # "Last 7 days" includes today, so window is 7 calendar days back.
        week_start = today_start - timedelta(days=6)
        today_hours = _completed_hours_in_range(account, today_start, tomorrow_start)
        week_hours = _completed_hours_in_range(account, week_start, tomorrow_start)

        return Response(
            {
                'active_punch': WorkerTimePunchSerializer(open_punch).data if open_punch else None,
                'punches': WorkerTimePunchSerializer(punches, many=True).data,
                'today_hours': today_hours,
                'week_hours': week_hours,
            }
        )

    action = str(request.data.get('action') or '').strip().lower()
    if action not in {'clock_in', 'clock_out', 'start_lunch', 'end_lunch'}:
        return Response(
            {'action': ['Use "clock_in", "clock_out", "start_lunch", or "end_lunch".']},
            status=status.HTTP_400_BAD_REQUEST,
        )

    site, site_err = _resolve_optional_work_site(request.data.get('work_site_id'))
    if site_err:
        return site_err

    geo = _parse_geo_payload(request.data.get('geolocation'))
    matched_site, geo_basic_ok, geo_basic_note, _geo_distance = _pitstop_geofence_validation(
        geo,
        preferred_site=site,
    )
    if action == 'clock_in' and matched_site and geo_basic_ok:
        site = matched_site
    now = timezone.now()

    open_punch = (
        WorkerTimePunch.objects.filter(worker_account=account, clock_out_at__isnull=True)
        .select_related('work_site', 'assignment', 'assignment__work_site')
        .order_by('-clock_in_at')
        .first()
    )

    if action in {'start_lunch', 'end_lunch'}:
        return _handle_lunch_action(action, open_punch, geo, now)

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
        clock_in_message = f'Clocked in at {site.name}.' if site else 'Clocked in.'
        return Response(
            {
                'message': clock_in_message,
                'punch': WorkerTimePunchSerializer(punch).data,
            },
            status=status.HTTP_201_CREATED,
        )

    if not open_punch:
        return Response(
            {'error': 'No active clock-in found.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if open_punch.is_on_lunch:
        return Response(
            {
                'error': 'End your lunch before clocking out.',
                'active_punch': WorkerTimePunchSerializer(open_punch).data,
            },
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
    clock_out_message = (
        f'Clocked out from {open_punch.work_site.name}.'
        if open_punch.work_site
        else 'Clocked out.'
    )
    return Response(
        {
            'message': clock_out_message,
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
