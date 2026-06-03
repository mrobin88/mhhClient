"""Staff SPA API — Django session auth (same credentials as admin)."""
from django.contrib.auth import authenticate, login, logout
from django.db.models import Q
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Client, CaseNote
from .staff_serializers import (
    StaffCaseNoteSerializer,
    StaffClientDetailSerializer,
    StaffClientListSerializer,
)
from .staff_utils import staff_display_name


def _staff_payload(user):
    return {
        'id': user.pk,
        'username': user.username,
        'display_name': staff_display_name(user),
        'role': getattr(user, 'role', ''),
        'is_superuser': bool(user.is_superuser),
    }


@api_view(['GET'])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def staff_csrf(request):
    return Response({'csrfToken': get_token(request)})


@api_view(['GET'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def staff_session(request):
    user = request.user
    if not user.is_staff:
        return Response({'authenticated': False}, status=status.HTTP_403_FORBIDDEN)
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
    return Response({'user': _staff_payload(user)})


@api_view(['POST'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def staff_logout(request):
    logout(request)
    return Response({'message': 'Logged out.'})


@api_view(['GET'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def staff_clients(request):
    if not request.user.is_staff:
        return Response({'error': 'Staff access required.'}, status=status.HTTP_403_FORBIDDEN)

    q = (request.GET.get('q') or '').strip()
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
    clients = queryset[:limit]
    return Response(StaffClientListSerializer(clients, many=True).data)


@api_view(['GET', 'PATCH'])
@authentication_classes([SessionAuthentication])
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
@authentication_classes([SessionAuthentication])
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
