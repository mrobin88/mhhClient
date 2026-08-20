"""Staff SPA API — Django session auth (same credentials as admin)."""
from collections import defaultdict
from datetime import timedelta
import logging
import re

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.db.models import Q
from django.middleware.csrf import get_token
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from .staff_auth import StaffSessionAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Client, CaseNote
from .models_extensions import ClientTextMessage
from .staff_serializers import (
    StaffCaseNoteSerializer,
    StaffClientCreateSerializer,
    StaffClientDetailSerializer,
    StaffClientListSerializer,
)
from .phone_utils import phone_digits
from .staff_utils import staff_display_name

ACCENT_HEX_RE = re.compile(r'^#[0-9A-Fa-f]{6}$')


def _staff_payload(user):
    collapsed = getattr(user, 'dashboard_collapsed', None)
    if not isinstance(collapsed, list):
        collapsed = []
    return {
        'id': user.pk,
        'username': user.username,
        'display_name': staff_display_name(user),
        'role': getattr(user, 'role', ''),
        'is_superuser': bool(user.is_superuser),
        'accent_color': (getattr(user, 'accent_color', None) or '').upper(),
        'dashboard_collapsed': [str(item)[:40] for item in collapsed if item],
    }


def _normalize_accent_color(value):
    raw = str(value or '').strip()
    if not raw:
        return ''
    if ACCENT_HEX_RE.fullmatch(raw):
        return raw.upper()
    return None


@api_view(['GET'])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def staff_csrf(request):
    return Response({'csrfToken': get_token(request)})


@api_view(['GET'])
@authentication_classes([StaffSessionAuthentication])
@permission_classes([AllowAny])
def staff_session(request):
    user = request.user
    if not user.is_authenticated or not user.is_staff:
        return Response({'authenticated': False})
    return Response({'authenticated': True, 'user': _staff_payload(user)})


@api_view(['POST'])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def staff_login(request):
    username = (request.data.get('username') or '').strip()
    password = request.data.get('password') or ''
    user = authenticate(request, username=username, password=password)
    if not user or not user.is_active or not user.is_staff:
        return Response(
            {'error': 'Invalid username or password.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    login(request, user)
    return Response({
        'authenticated': True,
        'user': _staff_payload(user),
        'csrfToken': get_token(request),
    })


@api_view(['POST'])
@authentication_classes([StaffSessionAuthentication])
@permission_classes([IsAuthenticated])
def staff_logout(request):
    logout(request)
    return Response({'message': 'Logged out.'})


@api_view(['PATCH'])
@authentication_classes([StaffSessionAuthentication])
@permission_classes([IsAuthenticated])
def staff_profile(request):
    """Save the signed-in staff member's dashboard preferences onto their account."""
    if not request.user.is_staff:
        return Response({'error': 'Staff access required.'}, status=status.HTTP_403_FORBIDDEN)

    update_fields = []

    if 'accent_color' in request.data:
        normalized = _normalize_accent_color(request.data.get('accent_color'))
        if normalized is None:
            return Response(
                {'error': 'Pick a color as a hex code like #EA580C.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        request.user.accent_color = normalized
        update_fields.append('accent_color')

    if 'dashboard_collapsed' in request.data:
        raw = request.data.get('dashboard_collapsed')
        if raw is None:
            collapsed = []
        elif isinstance(raw, list) and all(isinstance(item, str) and 0 < len(item) <= 40 for item in raw):
            collapsed = list(dict.fromkeys(raw[:24]))
        else:
            return Response(
                {'error': 'Could not save which dashboard cards are minimized.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        request.user.dashboard_collapsed = collapsed
        update_fields.append('dashboard_collapsed')

    if update_fields:
        request.user.save(update_fields=update_fields)

    return Response({'user': _staff_payload(request.user)})


@api_view(['GET'])
@authentication_classes([StaffSessionAuthentication])
@permission_classes([IsAuthenticated])
def staff_clients(request):
    if not request.user.is_staff:
        return Response({'error': 'Staff access required.'}, status=status.HTTP_403_FORBIDDEN)

    q = (request.GET.get('q') or '').strip()
    program = (request.GET.get('program') or '').strip()
    stage = (request.GET.get('stage') or '').strip()
    limit = min(int(request.GET.get('limit') or 40), 100)
    queryset = Client.objects.all().order_by('-updated_at')
    if q:
        digits = ''.join(ch for ch in q if ch.isdigit())
        filters = (
            Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(email__icontains=q)
            | Q(staff_name__icontains=q)
        )
        if digits:
            filters |= Q(phone__icontains=digits)
        queryset = queryset.filter(filters)
    if program in dict(Client.TRAINING_INTEREST_CHOICES):
        queryset = queryset.filter(training_interest=program)
    if stage in dict(Client.PIT_STOP_STAGE_CHOICES):
        queryset = queryset.filter(pit_stop_stage=stage)
    clients = queryset[:limit]
    return Response(StaffClientListSerializer(clients, many=True).data)


@api_view(['POST'])
@authentication_classes([StaffSessionAuthentication])
@permission_classes([IsAuthenticated])
def staff_client_create(request):
    """Create a minimal client from an outside referral, with duplicate warning."""
    if not request.user.is_staff:
        return Response({'error': 'Staff access required.'}, status=status.HTTP_403_FORBIDDEN)

    serializer = StaffClientCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    phone = phone_digits(serializer.validated_data.get('phone'))
    email = str(serializer.validated_data.get('email') or '').strip()
    duplicate_ids = set()
    if phone:
        duplicate_ids.update(
            client.pk for client in Client.objects.only('pk', 'phone')
            if phone_digits(client.phone) == phone
        )
    if email:
        duplicate_ids.update(
            Client.objects.filter(email__iexact=email).values_list('pk', flat=True)
        )
    if duplicate_ids and not request.data.get('confirm_duplicate'):
        matches = Client.objects.filter(pk__in=duplicate_ids).order_by('-updated_at')
        return Response(
            {
                'error': 'A client with this phone or email may already exist.',
                'duplicates': StaffClientListSerializer(matches, many=True).data,
                'requires_confirmation': True,
            },
            status=status.HTTP_409_CONFLICT,
        )

    client = serializer.save()
    from .staff_utils import apply_staff_assignment_to_client
    apply_staff_assignment_to_client(client, request.user)
    client.save(update_fields=['staff_name'])
    return Response(
        StaffClientDetailSerializer(client).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(['GET', 'PATCH'])
@authentication_classes([StaffSessionAuthentication])
@permission_classes([IsAuthenticated])
def staff_client_detail(request, pk):
    if not request.user.is_staff:
        return Response({'error': 'Staff access required.'}, status=status.HTTP_403_FORBIDDEN)

    try:
        client = Client.objects.get(pk=pk)
    except Client.DoesNotExist:
        return Response({'error': 'Client not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(StaffClientDetailSerializer(client).data)

    from .staff_utils import apply_staff_assignment_to_client

    serializer = StaffClientDetailSerializer(client, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    apply_staff_assignment_to_client(client, request.user)
    client.save(update_fields=['staff_name'])
    return Response(StaffClientDetailSerializer(client).data)


@api_view(['GET', 'POST'])
@authentication_classes([StaffSessionAuthentication])
@permission_classes([IsAuthenticated])
def staff_client_notes(request, pk):
    if not request.user.is_staff:
        return Response({'error': 'Staff access required.'}, status=status.HTTP_403_FORBIDDEN)

    try:
        client = Client.objects.get(pk=pk)
    except Client.DoesNotExist:
        return Response({'error': 'Client not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        notes = (
            CaseNote.objects.filter(client=client)
            .order_by('-note_date', '-created_at')[:50]
        )
        return Response(StaffCaseNoteSerializer(notes, many=True).data)

    serializer = StaffCaseNoteSerializer(data={**request.data, 'client': client.pk})
    serializer.is_valid(raise_exception=True)
    note = serializer.save(staff_member=staff_display_name(request.user))
    return Response(StaffCaseNoteSerializer(note).data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@authentication_classes([StaffSessionAuthentication])
@permission_classes([IsAuthenticated])
def staff_client_pitstop_promote(request, pk):
    """
    Give a Pit Stop client worker portal access.

    Creating the WorkerAccount is what moves the client to the 'worker' stage
    (see WorkerAccount.save), so staff no longer need Django admin for this.
    """
    if not request.user.is_staff:
        return Response({'error': 'Staff access required.'}, status=status.HTTP_403_FORBIDDEN)

    try:
        client = Client.objects.get(pk=pk)
    except Client.DoesNotExist:
        return Response({'error': 'Client not found.'}, status=status.HTTP_404_NOT_FOUND)

    from .models_extensions import WorkerAccount
    from .phone_utils import default_worker_pin_from_phone, normalize_login_phone

    if getattr(client, 'worker_account', None) is not None:
        return Response(
            {'error': 'This client already has worker portal access.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    normalized_phone = normalize_login_phone(client.phone)
    if len(normalized_phone) < 10:
        return Response(
            {
                'error': (
                    'A valid 10-digit phone number is required for worker login. '
                    'Update the phone on this client first.'
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if WorkerAccount.objects.filter(phone=normalized_phone).exists():
        return Response(
            {'error': 'Another worker already uses this phone number for login.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    account = WorkerAccount(
        client=client,
        phone=normalized_phone,
        is_active=True,
        worker_status=WorkerAccount.STATUS_ACTIVE,
        created_by=request.user.username,
    )
    account.set_pin(default_worker_pin_from_phone(normalized_phone))
    account.save()

    client.refresh_from_db()
    return Response(
        {
            'message': 'Worker portal access created. PIN is the last 4 digits of their phone.',
            'client': StaffClientDetailSerializer(client).data,
        },
        status=status.HTTP_201_CREATED,
    )


def _staff_reset_email_link(request, user):
    """Deep link into staff SPA hash router for password reset."""
    base = getattr(settings, 'STAFF_APP_BASE_URL', '').rstrip('/')
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return f'{base}/#/reset-password/{uid}/{token}'


@api_view(['POST'])
@permission_classes([AllowAny])
def staff_password_reset(request):
    """Request password reset email (always returns success message)."""
    email = (request.data.get('email') or '').strip()
    if not email:
        return Response({'error': 'Enter your work email.'}, status=status.HTTP_400_BAD_REQUEST)

    StaffUser = get_user_model()
    users = StaffUser.objects.filter(email__iexact=email, is_staff=True, is_active=True)
    for user in users:
        reset_url = _staff_reset_email_link(request, user)
        from django.core.mail import send_mail

        try:
            send_mail(
                subject='Reset your Mission Hiring Hall staff password',
                message=(
                    f'Hi {user.get_full_name() or user.username},\n\n'
                    f'Use this link to reset your password (expires in 24 hours):\n{reset_url}\n\n'
                    'If you did not request this, ignore this email.'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
        except Exception:
            logging.getLogger('clients').exception(
                'Staff password reset email failed for user id %s.', user.pk
            )

    return Response({
        'message': 'If that email is registered, you will receive reset instructions shortly.',
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def staff_password_reset_confirm(request):
    uidb64 = request.data.get('uid')
    token = request.data.get('token')
    new_password = request.data.get('new_password') or ''

    if not uidb64 or not token:
        return Response({'error': 'Invalid reset link.'}, status=status.HTTP_400_BAD_REQUEST)

    StaffUser = get_user_model()
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = StaffUser.objects.get(pk=uid, is_staff=True, is_active=True)
    except (TypeError, ValueError, OverflowError, StaffUser.DoesNotExist):
        return Response(
            {'error': 'This reset link is invalid or expired. Request a new one.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not default_token_generator.check_token(user, token):
        return Response(
            {'error': 'This reset link is invalid or expired. Request a new one.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    form = SetPasswordForm(user, {'new_password1': new_password, 'new_password2': new_password})
    if not form.is_valid():
        first_error = next(iter(form.errors.values()))[0]
        return Response({'error': str(first_error)}, status=status.HTTP_400_BAD_REQUEST)

    form.save()
    return Response({'message': 'Password updated. You can sign in now.'})


@api_view(['GET'])
@authentication_classes([StaffSessionAuthentication])
@permission_classes([IsAuthenticated])
def staff_messages_unread_count(request):
    if not request.user.is_staff:
        return Response({'error': 'Staff access required.'}, status=status.HTTP_403_FORBIDDEN)

    since = timezone.now() - timedelta(days=7)
    count = ClientTextMessage.objects.filter(
        direction=ClientTextMessage.DIRECTION_INBOUND,
        status=ClientTextMessage.STATUS_RECEIVED,
        created_at__gte=since,
    ).count()
    return Response({'count': count})


@api_view(['GET'])
@authentication_classes([StaffSessionAuthentication])
@permission_classes([IsAuthenticated])
def staff_messages(request):
    """Client SMS threads for staff messaging hub (poll for updates)."""
    if not request.user.is_staff:
        return Response({'error': 'Staff access required.'}, status=status.HTTP_403_FORBIDDEN)

    since = timezone.now() - timedelta(days=30)
    messages = (
        ClientTextMessage.objects.filter(created_at__gte=since)
        .select_related('client')
        .order_by('-created_at')[:200]
    )

    grouped = defaultdict(list)
    for msg in messages:
        at = msg.sent_at or msg.received_at or msg.created_at
        grouped[msg.client_id].append({
            'id': msg.pk,
            'direction': msg.direction,
            'body': msg.body,
            'at': at.isoformat() if at else '',
            'status': msg.status,
        })

    threads = []
    for client_id, msgs in grouped.items():
        client = Client.objects.filter(pk=client_id).first()
        if not client:
            continue
        latest = msgs[0]
        threads.append({
            'client_id': client_id,
            'client_name': client.full_name,
            'preview': latest['body'][:140],
            'last_at': latest['at'],
            'unread': latest['direction'] == ClientTextMessage.DIRECTION_INBOUND
            and latest['status'] == ClientTextMessage.STATUS_RECEIVED,
            'messages': list(reversed(msgs[-40:])),
        })

    threads.sort(key=lambda t: t['last_at'], reverse=True)
    return Response({'threads': threads})
