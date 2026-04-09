"""
Worker Portal API — open shifts + “I’m interested” (no scheduling, no call-out forms).
"""
from datetime import date, timedelta

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
)
from .serializers import (
    WorkerLoginSerializer,
    WorkerAccountSerializer,
    OpenShiftSerializer,
    ShiftCoverInterestSerializer,
    ShiftCoverInterestStaffSerializer,
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
