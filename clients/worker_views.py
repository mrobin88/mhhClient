"""
Worker Portal API — open shifts + “I’m interested” (no scheduling, no call-out forms).
"""
from datetime import date, datetime, timedelta, timezone as dt_timezone

from django.utils import timezone
from rest_framework import status
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models_extensions import (
    WorkerAccount,
    WorkerSessionToken,
    OpenShift,
    ShiftCoverInterest,
    WorkerTimePunch,
)
from .serializers import (
    WorkerLoginSerializer,
    WorkerAccountSerializer,
    OpenShiftSerializer,
    ShiftCoverInterestSerializer,
    ShiftCoverInterestStaffSerializer,
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
    token = _worker_token(request)
    session = WorkerSession.get_session(token)
    if not session:
        return Response(
            {'error': 'Invalid or expired session'},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    try:
        worker_account = WorkerAccount.objects.select_related('client').get(
            id=session['worker_account_id']
        )
        return Response(WorkerAccountSerializer(worker_account).data)
    except WorkerAccount.DoesNotExist:
        return Response(
            {'error': 'Worker account not found'},
            status=status.HTTP_404_NOT_FOUND,
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def worker_open_shifts(request):
    """List shifts that still need coverage (staff posts these)."""
    _, err = _require_worker(request)
    if err:
        return err

    today = date.today()
    shifts = (
        OpenShift.objects.filter(is_open=True, shift_date__gte=today)
        .select_related('work_site')
        .order_by('shift_date', 'start_time')
    )
    return Response(OpenShiftSerializer(shifts, many=True).data)


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def worker_shift_interests(request):
    """GET: this worker’s interests. POST: express interest in an open shift."""
    account, err = _require_worker(request)
    if err:
        return err

    if request.method == 'GET':
        qs = (
            ShiftCoverInterest.objects.filter(worker_account=account)
            .select_related('open_shift', 'open_shift__work_site')
            .order_by('-created_at')
        )
        return Response(ShiftCoverInterestSerializer(qs, many=True).data)

    open_shift_id = request.data.get('open_shift_id')
    if open_shift_id is None:
        return Response(
            {'open_shift_id': ['This field is required.']},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        open_shift_id = int(open_shift_id)
    except (TypeError, ValueError):
        return Response(
            {'open_shift_id': ['Invalid id.']},
            status=status.HTTP_400_BAD_REQUEST,
        )

    today = date.today()
    try:
        shift = OpenShift.objects.get(
            pk=open_shift_id,
            is_open=True,
            shift_date__gte=today,
        )
    except OpenShift.DoesNotExist:
        return Response(
            {'error': 'That shift is not available anymore.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    existing = ShiftCoverInterest.objects.filter(
        worker_account=account,
        open_shift=shift,
    ).first()
    if existing:
        return Response(
            {
                'error': 'You already let us know for this shift.',
                'interest': ShiftCoverInterestSerializer(existing).data,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    interest = ShiftCoverInterest.objects.create(
        worker_account=account,
        open_shift=shift,
        status=ShiftCoverInterest.STATUS_PENDING,
    )
    interest = ShiftCoverInterest.objects.select_related(
        'open_shift', 'open_shift__work_site'
    ).get(pk=interest.pk)
    return Response(ShiftCoverInterestSerializer(interest).data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def worker_time_punch(request):
    """Worker clock in/out with optional geolocation and server time context."""
    account, err = _require_worker(request)
    if err:
        return err

    if request.method == 'GET':
        open_punch = (
            WorkerTimePunch.objects.filter(worker_account=account, clock_out_at__isnull=True)
            .order_by('-clock_in_at')
            .first()
        )
        recent = WorkerTimePunch.objects.filter(worker_account=account).order_by('-clock_in_at')[:10]
        return Response(
            {
                'server_time': timezone.now(),
                'is_clocked_in': open_punch is not None,
                'active_punch': WorkerTimePunchSerializer(open_punch).data if open_punch else None,
                'recent_punches': WorkerTimePunchSerializer(recent, many=True).data,
            }
        )

    action = str(request.data.get('action') or '').strip().lower()
    if action not in {'clock_in', 'clock_out'}:
        return Response(
            {'action': ['Action must be "clock_in" or "clock_out".']},
            status=status.HTTP_400_BAD_REQUEST,
        )

    geo = _parse_geo_payload(request.data.get('geolocation'))
    now = timezone.now()

    open_punch = (
        WorkerTimePunch.objects.filter(worker_account=account, clock_out_at__isnull=True)
        .order_by('-clock_in_at')
        .first()
    )

    if action == 'clock_in':
        if open_punch:
            return Response(
                {'error': 'You are already clocked in.', 'active_punch': WorkerTimePunchSerializer(open_punch).data},
                status=status.HTTP_400_BAD_REQUEST,
            )
        punch = WorkerTimePunch.objects.create(
            worker_account=account,
            clock_in_at=now,
            clock_in_client_reported_at=geo['client_reported_at'],
            clock_in_latitude=geo['latitude'],
            clock_in_longitude=geo['longitude'],
            clock_in_accuracy_meters=geo['accuracy'],
            clock_in_geo_status=geo['status'],
            clock_in_geo_error=geo['error'],
        )
        return Response(
            {
                'server_time': now,
                'message': 'Clock-in recorded.',
                'punch': WorkerTimePunchSerializer(punch).data,
            },
            status=status.HTTP_201_CREATED,
        )

    if not open_punch:
        return Response({'error': 'No active clock-in found.'}, status=status.HTTP_400_BAD_REQUEST)

    open_punch.clock_out_at = now
    open_punch.clock_out_server_received_at = now
    open_punch.clock_out_client_reported_at = geo['client_reported_at']
    open_punch.clock_out_latitude = geo['latitude']
    open_punch.clock_out_longitude = geo['longitude']
    open_punch.clock_out_accuracy_meters = geo['accuracy']
    open_punch.clock_out_geo_status = geo['status']
    open_punch.clock_out_geo_error = geo['error']
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
        ]
    )
    return Response(
        {
            'server_time': now,
            'message': 'Clock-out recorded.',
            'punch': WorkerTimePunchSerializer(open_punch).data,
        }
    )


@api_view(['PATCH'])
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def staff_shift_interest_update(request, pk):
    """
    Staff/supervisor: set status (selected / not_selected / pending / cancelled).
    Uses Django session login (admin user).
    """
    if not request.user.is_staff:
        return Response({'detail': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

    try:
        interest = ShiftCoverInterest.objects.select_related(
            'open_shift', 'worker_account__client'
        ).get(pk=pk)
    except ShiftCoverInterest.DoesNotExist:
        return Response({'detail': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = ShiftCoverInterestStaffSerializer(
        interest,
        data=request.data,
        partial=True,
    )
    if serializer.is_valid():
        serializer.save()
        return Response(
            ShiftCoverInterestSerializer(
                ShiftCoverInterest.objects.select_related(
                    'open_shift', 'open_shift__work_site'
                ).get(pk=interest.pk)
            ).data
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
