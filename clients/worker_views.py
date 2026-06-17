"""
Worker Portal API — worker clock in/out with optional map snapshot reference.
"""
import json
from datetime import timedelta
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
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import CaseNote
from .models_extensions import (
    WorkerAccount,
    WorkerDailyFeedback,
    WorkerSessionToken,
    WorkSite,
    WorkerTimePunch,
)
from .serializers import (
    WorkerLoginSerializer,
    WorkerAccountSerializer,
    WorkerDailyFeedbackSerializer,
    WorkSiteSerializer,
    WorkerTimePunchSerializer,
)
from .throttles import WorkerPunchThrottle
from .time_display import display_tz
from .worker_map_utils import fetch_static_map_image

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


def _parse_optional_coordinates(request):
    """Optional map center coords (for server-side static map only, not validated)."""
    lat = request.data.get('map_latitude')
    lng = request.data.get('map_longitude')
    if lat is None or lng is None:
        geo_raw = request.data.get('geolocation')
        if isinstance(geo_raw, str):
            try:
                geo_raw = json.loads(geo_raw)
            except json.JSONDecodeError:
                geo_raw = None
        if isinstance(geo_raw, dict):
            lat = geo_raw.get('latitude')
            lng = geo_raw.get('longitude')
    try:
        if lat is None or lng is None:
            return None, None
        return float(lat), float(lng)
    except (TypeError, ValueError):
        return None, None


def _parse_geolocation_payload(request):
    """Normalized geolocation payload from JSON body or multipart fields."""
    geo_raw = request.data.get('geolocation')
    payload = {}
    if isinstance(geo_raw, str):
        try:
            payload = json.loads(geo_raw)
        except json.JSONDecodeError:
            payload = {}
    elif isinstance(geo_raw, dict):
        payload = geo_raw

    latitude, longitude = _parse_optional_coordinates(request)
    if latitude is None:
        latitude = payload.get('latitude')
    if longitude is None:
        longitude = payload.get('longitude')

    try:
        latitude = float(latitude) if latitude is not None else None
    except (TypeError, ValueError):
        latitude = None
    try:
        longitude = float(longitude) if longitude is not None else None
    except (TypeError, ValueError):
        longitude = None

    try:
        accuracy = payload.get('accuracy')
        accuracy = float(accuracy) if accuracy is not None else None
    except (TypeError, ValueError):
        accuracy = None

    status_value = str(payload.get('status') or '').strip().lower()
    geo_status = status_value if status_value in dict(WorkerTimePunch.GEO_STATUS_CHOICES) else None
    geo_error = str(payload.get('error') or '').strip()[:200]
    has_coordinates = latitude is not None and longitude is not None
    if not geo_status:
        geo_status = WorkerTimePunch.GEO_STATUS_CAPTURED if has_coordinates else WorkerTimePunch.GEO_STATUS_SKIPPED

    return {
        'latitude': latitude,
        'longitude': longitude,
        'accuracy': accuracy,
        'status': geo_status,
        'error': geo_error,
        'has_coordinates': has_coordinates,
    }


def _location_required_error(action):
    action_label = action.replace('_', ' ')
    return Response(
        {'error': f'Turn on location services to {action_label}.'},
        status=status.HTTP_400_BAD_REQUEST,
    )


def _parse_location_reference(request):
    """Map snapshot file + human-readable label from clock in/out POST."""
    label = str(request.data.get('location_label') or '').strip()[:300]
    map_file = request.FILES.get('map_snapshot')
    latitude, longitude = _parse_optional_coordinates(request)
    return {
        'label': label,
        'map_file': map_file,
        'latitude': latitude,
        'longitude': longitude,
    }


def _attach_location_snapshot(punch, prefix, location_ref):
    """Save label and map image on clock-in or clock-out (no validation)."""
    label_field = f'{prefix}_location_label'
    map_field = f'{prefix}_map_image'
    setattr(punch, label_field, location_ref.get('label') or '')

    uploaded = location_ref.get('map_file')
    if uploaded:
        getattr(punch, map_field).save(uploaded.name, uploaded, save=False)
        return

    lat = location_ref.get('latitude')
    lng = location_ref.get('longitude')
    if lat is None or lng is None:
        return
    content = fetch_static_map_image(lat, lng)
    if content:
        getattr(punch, map_field).save(content.name, content, save=False)


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


@api_view(['PATCH'])
@permission_classes([AllowAny])
def worker_profile_update(request):
    worker_account, err = _require_worker(request)
    if err:
        return err

    short_profile = request.data.get('short_profile')
    career_goals = request.data.get('long_term_career_goals')
    update_fields = []

    if short_profile is not None:
        worker_account.short_profile = str(short_profile).strip()[:1200]
        update_fields.append('short_profile')
    if career_goals is not None:
        worker_account.long_term_career_goals = str(career_goals).strip()[:2000]
        update_fields.append('long_term_career_goals')

    if not update_fields:
        return Response(
            {'error': 'Provide short_profile or long_term_career_goals.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    worker_account.save(update_fields=update_fields + ['is_approved'])
    return Response(WorkerAccountSerializer(worker_account).data)


def _worker_local_today():
    return timezone.now().astimezone(WORKER_LOCAL_TZ).date()


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def worker_daily_feedback(request):
    worker_account, err = _require_worker(request)
    if err:
        return err

    if request.method == 'GET':
        today = _worker_local_today()
        todays_entry = WorkerDailyFeedback.objects.filter(
            worker_account=worker_account,
            feedback_date=today,
        ).first()
        recent_entries = WorkerDailyFeedback.objects.filter(worker_account=worker_account)[:7]
        return Response(
            {
                'today_feedback': (
                    WorkerDailyFeedbackSerializer(todays_entry).data if todays_entry else None
                ),
                'recent_feedback': WorkerDailyFeedbackSerializer(recent_entries, many=True).data,
            }
        )

    feedback_text = str(request.data.get('feedback_text') or '').strip()
    if not feedback_text:
        return Response(
            {'feedback_text': ['Tell us how your day went.']},
            status=status.HTTP_400_BAD_REQUEST,
        )

    feedback_date = _worker_local_today()
    entry, created = WorkerDailyFeedback.objects.update_or_create(
        worker_account=worker_account,
        feedback_date=feedback_date,
        defaults={'feedback_text': feedback_text[:2000]},
    )
    return Response(
        {
            'message': 'Daily feedback saved.' if created else 'Daily feedback updated.',
            'feedback': WorkerDailyFeedbackSerializer(entry).data,
        },
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


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
    """Active PitStop sites (optional reference; clock flow does not require selection)."""
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


def _handle_lunch_action(action, open_punch, now, geolocation):
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
        if not geolocation['has_coordinates']:
            return _location_required_error(action)
        open_punch.lunch_start_at = now
        open_punch.lunch_start_latitude = geolocation['latitude']
        open_punch.lunch_start_longitude = geolocation['longitude']
        open_punch.save(
            update_fields=['lunch_start_at', 'lunch_start_latitude', 'lunch_start_longitude']
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
    if not geolocation['has_coordinates']:
        return _location_required_error(action)
    open_punch.lunch_end_at = now
    open_punch.lunch_end_latitude = geolocation['latitude']
    open_punch.lunch_end_longitude = geolocation['longitude']
    open_punch.save(
        update_fields=['lunch_end_at', 'lunch_end_latitude', 'lunch_end_longitude']
    )
    return Response(
        {
            'message': f'Lunch ended ({open_punch.lunch_minutes} min).',
            'punch': WorkerTimePunchSerializer(open_punch).data,
        }
    )


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser, JSONParser])
@throttle_classes([WorkerPunchThrottle])
def worker_time_punch(request):
    """Worker clock in/out; optional map snapshot + location label (no geofence)."""
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

    geolocation = _parse_geolocation_payload(request)
    location_ref = _parse_location_reference(request) if action in {'clock_in', 'clock_out'} else None
    now = timezone.now()

    open_punch = (
        WorkerTimePunch.objects.filter(worker_account=account, clock_out_at__isnull=True)
        .select_related('work_site', 'assignment', 'assignment__work_site')
        .order_by('-clock_in_at')
        .first()
    )

    if action in {'start_lunch', 'end_lunch'}:
        return _handle_lunch_action(action, open_punch, now, geolocation)

    if action == 'clock_in':
        if open_punch:
            return Response(
                {
                    'error': 'You are already clocked in. Clock out first.',
                    'active_punch': WorkerTimePunchSerializer(open_punch).data,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not geolocation['has_coordinates']:
            return _location_required_error(action)
        punch = WorkerTimePunch.objects.create(
            worker_account=account,
            work_site=site,
            clock_in_at=now,
            clock_in_latitude=geolocation['latitude'],
            clock_in_longitude=geolocation['longitude'],
            clock_in_accuracy_meters=geolocation['accuracy'],
            clock_in_geo_status=geolocation['status'],
            clock_in_geo_error=geolocation['error'],
            clock_in_geo_basic_ok=True,
            clock_in_geo_basic_note='Location captured',
        )
        if location_ref:
            _attach_location_snapshot(punch, 'clock_in', location_ref)
            punch.save(
                update_fields=['clock_in_location_label', 'clock_in_map_image'],
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
    if not geolocation['has_coordinates']:
        return _location_required_error(action)

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
    open_punch.clock_out_latitude = geolocation['latitude']
    open_punch.clock_out_longitude = geolocation['longitude']
    open_punch.clock_out_accuracy_meters = geolocation['accuracy']
    open_punch.clock_out_geo_status = geolocation['status']
    open_punch.clock_out_geo_error = geolocation['error']
    open_punch.clock_out_geo_basic_ok = True
    open_punch.clock_out_geo_basic_note = 'Location captured'
    update_fields = [
        'clock_out_at',
        'clock_out_server_received_at',
        'clock_out_latitude',
        'clock_out_longitude',
        'clock_out_accuracy_meters',
        'clock_out_geo_status',
        'clock_out_geo_error',
        'clock_out_geo_basic_ok',
        'clock_out_geo_basic_note',
    ]
    if location_ref:
        _attach_location_snapshot(open_punch, 'clock_out', location_ref)
        update_fields.extend(['clock_out_location_label', 'clock_out_map_image'])
    open_punch.save(update_fields=update_fields)
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


@api_view(['POST'])
@permission_classes([AllowAny])
def worker_incident_report(request):
    """Simple worker incident report for supervisor follow-up."""
    account, err = _require_worker(request)
    if err:
        return err

    supervisor_name = str(request.data.get('supervisor_name') or '').strip()
    details = str(request.data.get('details') or '').strip()
    if not supervisor_name:
        return Response(
            {'supervisor_name': ['Supervisor name is required.']},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not details:
        return Response(
            {'details': ['Describe what happened.']},
            status=status.HTTP_400_BAD_REQUEST,
        )

    CaseNote.objects.create(
        client=account.client,
        staff_member='Worker Portal',
        note_type='general',
        content=(
            'Worker Incident Report\n'
            f'Supervisor: {supervisor_name}\n'
            f'What happened: {details}'
        ),
    )
    return Response({'message': 'Incident report submitted.'}, status=status.HTTP_201_CREATED)


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
