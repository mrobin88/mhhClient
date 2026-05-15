"""
Worker Portal API — open shifts + “I’m interested” (no scheduling, no call-out forms).
"""
import json
from datetime import date, datetime, timedelta, timezone as dt_timezone

from django.core.exceptions import ValidationError
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
    WorkAssignment,
    OpenShift,
    ShiftCoverInterest,
    WorkerTimePunch,
    WorkerShiftProof,
    WorkerPortalNote,
    WorkerTimeOffRequest,
)
from .serializers import (
    WorkerLoginSerializer,
    WorkerAccountSerializer,
    OpenShiftSerializer,
    ShiftCoverInterestSerializer,
    ShiftCoverInterestStaffSerializer,
    WorkAssignmentSerializer,
    WorkerShiftProofSerializer,
    WorkerPortalNoteSerializer,
    WorkerTimeOffRequestSerializer,
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


def _proof_assignment_for_worker(account, assignment_id):
    if not assignment_id:
        return None, Response(
            {'assignment_id': ['Choose the assignment you are checking in for.']},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        assignment = WorkAssignment.objects.select_related('work_site', 'client').get(
            pk=assignment_id,
            client=account.client,
        )
    except (TypeError, ValueError, WorkAssignment.DoesNotExist):
        return None, Response(
            {'error': 'Assignment not found.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if assignment.status in {'cancelled', 'called_out'}:
        return None, Response(
            {'error': 'This assignment is not available for photo check-in.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return assignment, None


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
    """Upcoming/current assignments for the simplified worker portal."""
    account, err = _require_worker(request)
    if err:
        return err

    today = timezone.localdate()
    assignments = (
        WorkAssignment.objects.filter(
            client=account.client,
            assignment_date__gte=today - timedelta(days=1),
        )
        .exclude(status__in=['cancelled', 'called_out'])
        .select_related('work_site', 'client')
        .order_by('assignment_date', 'start_time')[:20]
    )
    latest_proofs = {}
    proofs = (
        WorkerShiftProof.objects.filter(worker_account=account, assignment__in=assignments)
        .select_related('assignment', 'assignment__work_site')
        .order_by('assignment_id', '-submitted_at')
    )
    for proof in proofs:
        latest_proofs.setdefault(proof.assignment_id, proof)
    payload = []
    for assignment in assignments:
        latest_proof = latest_proofs.get(assignment.id)
        row = WorkAssignmentSerializer(assignment).data
        row['can_submit_proof'] = assignment.status not in {'cancelled', 'called_out'}
        row['latest_proof'] = WorkerShiftProofSerializer(latest_proof).data if latest_proof else None
        row['proof_submitted'] = latest_proof is not None
        payload.append(row)
    return Response(payload)


@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
@permission_classes([AllowAny])
def worker_shift_proof(request):
    """Save a worker photo check-in with browser location."""
    account, err = _require_worker(request)
    if err:
        return err

    assignment, assignment_err = _proof_assignment_for_worker(
        account,
        request.data.get('assignment_id'),
    )
    if assignment_err:
        return assignment_err

    photo = request.FILES.get('photo')
    if not photo:
        return Response(
            {'photo': ['Take or choose a photo before submitting.']},
            status=status.HTTP_400_BAD_REQUEST,
        )

    geo = _parse_geo_payload(request.data.get('geolocation'))
    geo_basic_ok, geo_basic_note = _basic_geo_validation(geo)
    proof = WorkerShiftProof.objects.create(
        worker_account=account,
        assignment=assignment,
        photo=photo,
        client_reported_at=geo['client_reported_at'],
        latitude=geo['latitude'],
        longitude=geo['longitude'],
        accuracy_meters=geo['accuracy'],
        geo_status=geo['status'],
        geo_error=geo['error'],
        geo_basic_ok=geo_basic_ok,
        geo_basic_note=geo_basic_note,
    )
    return Response(
        {
            'message': 'Photo and location sent to staff.',
            'proof': WorkerShiftProofSerializer(proof).data,
        },
        status=status.HTTP_201_CREATED,
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
    """Legacy endpoint retained so old clients fail clearly instead of clocking workers."""
    account, err = _require_worker(request)
    if err:
        return err

    return Response(
        {'error': 'Clock in/out has been replaced by photo check-in.'},
        status=status.HTTP_410_GONE,
    )


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def worker_notes(request):
    """Worker notes timeline + submission."""
    account, err = _require_worker(request)
    if err:
        return err

    if request.method == 'GET':
        notes = WorkerPortalNote.objects.filter(worker_account=account).order_by('-created_at')[:30]
        return Response(WorkerPortalNoteSerializer(notes, many=True).data)

    note_type = str(request.data.get('note_type') or WorkerPortalNote.TYPE_GENERAL).strip()
    if note_type not in {x[0] for x in WorkerPortalNote.NOTE_TYPE_CHOICES}:
        return Response({'note_type': ['Invalid note type.']}, status=status.HTTP_400_BAD_REQUEST)

    content = str(request.data.get('content') or '').strip()
    if not content:
        return Response({'content': ['Note text is required.']}, status=status.HTTP_400_BAD_REQUEST)
    if len(content) > 4000:
        return Response({'content': ['Note is too long.']}, status=status.HTTP_400_BAD_REQUEST)

    note = WorkerPortalNote.objects.create(
        worker_account=account,
        note_type=note_type,
        content=content,
    )
    return Response(WorkerPortalNoteSerializer(note).data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def worker_time_off_requests(request):
    """Worker time-off requests timeline + submission."""
    account, err = _require_worker(request)
    if err:
        return err

    if request.method == 'GET':
        rows = WorkerTimeOffRequest.objects.filter(worker_account=account).order_by('-created_at')[:30]
        return Response(WorkerTimeOffRequestSerializer(rows, many=True).data)

    start_date_raw = request.data.get('start_date')
    end_date_raw = request.data.get('end_date')
    reason = str(request.data.get('reason') or '').strip()
    if not reason:
        return Response({'reason': ['Reason is required.']}, status=status.HTTP_400_BAD_REQUEST)
    if len(reason) > 4000:
        return Response({'reason': ['Reason is too long.']}, status=status.HTTP_400_BAD_REQUEST)

    try:
        start_date = date.fromisoformat(str(start_date_raw))
        end_date = date.fromisoformat(str(end_date_raw))
    except Exception:
        return Response(
            {'start_date': ['Use YYYY-MM-DD dates.'], 'end_date': ['Use YYYY-MM-DD dates.']},
            status=status.HTTP_400_BAD_REQUEST,
        )

    req = WorkerTimeOffRequest(
        worker_account=account,
        start_date=start_date,
        end_date=end_date,
        reason=reason,
    )
    try:
        req.full_clean()
    except ValidationError:
        return Response(
            {'end_date': ['End date cannot be before start date.']},
            status=status.HTTP_400_BAD_REQUEST,
        )
    req.save()
    return Response(WorkerTimeOffRequestSerializer(req).data, status=status.HTTP_201_CREATED)


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
