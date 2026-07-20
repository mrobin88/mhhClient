"""
Staff Dashboard API — session-authenticated, staff-only.

Single-tenant (Mission Hiring Hall only): no org scoping. Every endpoint here
reads directly from existing models; none of this forks or duplicates admin
business logic.
"""
import io
import logging
from datetime import timedelta
from pathlib import Path

from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db.models import Count
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Client, Document
from .staff_auth import StaffSessionAuthentication
from .staff_utils import staff_display_name
from .views import (
    ALLOWED_SUPPORTING_DOC_EXTENSIONS,
    MAX_SUPPORTING_DOC_UPLOAD_BYTES,
    _validate_uploaded_file,
)

logger = logging.getLogger('clients')
User = get_user_model()

# Conservative image compression: only resize when clearly larger than needed for
# on-screen/print review, keep quality high so IDs and consent forms stay legible.
IMAGE_MAX_DIMENSION = 2000
IMAGE_JPEG_QUALITY = 85
COMPRESSIBLE_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}


def _staff_guard(request):
    """Return an error Response if the caller is not authenticated staff, else None."""
    user = request.user
    if not user or not user.is_authenticated or not user.is_staff:
        return Response({'error': 'Staff access required.'}, status=status.HTTP_403_FORBIDDEN)
    return None


@api_view(['GET'])
@authentication_classes([StaffSessionAuthentication])
@permission_classes([IsAuthenticated])
def dashboard_recent_clients(request):
    """Last 5 clients added, for the Recent Clients module."""
    err = _staff_guard(request)
    if err:
        return err

    limit = min(int(request.GET.get('limit') or 5), 20)
    clients = Client.objects.order_by('-created_at')[:limit]
    data = [
        {
            'id': c.id,
            'full_name': c.full_name,
            'created_at': c.created_at,
            'training_interest': c.training_interest,
            'training_interest_display': c.get_training_interest_display(),
            'status': c.status,
        }
        for c in clients
    ]
    return Response({'results': data})


@api_view(['GET'])
@authentication_classes([StaffSessionAuthentication])
@permission_classes([IsAuthenticated])
def dashboard_program_distribution(request):
    """Client counts grouped by program (training_interest), for the chart module."""
    err = _staff_guard(request)
    if err:
        return err

    display_map = dict(Client.TRAINING_INTEREST_CHOICES)
    rows = (
        Client.objects.values('training_interest')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    data = [
        {
            'program': row['training_interest'],
            'program_display': display_map.get(row['training_interest'], row['training_interest']),
            'count': row['count'],
        }
        for row in rows
    ]
    return Response({'results': data, 'category_count': len(data)})


def _client_ids_for_log_entries(entries):
    """
    Map LogEntry.id -> client_id when the logged object is a Client or
    another clients.* model that points at a Client (case notes, docs, etc.).
    Lets the staff dashboard turn "Ada Xie - general - 07/15/2026" into a link.
    """
    from .models import CaseNote, Document, PitStopApplication
    from .models_classes import ClassEnrollment

    by_model = {}
    for e in entries:
        if not e.content_type_id or not e.object_id:
            continue
        key = (e.content_type.app_label, e.content_type.model)
        by_model.setdefault(key, []).append(e)

    resolved = {}

    client_entries = by_model.get(('clients', 'client'), [])
    for e in client_entries:
        try:
            resolved[e.id] = int(e.object_id)
        except (TypeError, ValueError):
            pass

    def _map_fk(model_key, Model, client_field='client_id'):
        bucket = by_model.get(model_key, [])
        if not bucket:
            return
        ids = []
        for e in bucket:
            try:
                ids.append(int(e.object_id))
            except (TypeError, ValueError):
                continue
        if not ids:
            return
        rows = Model.objects.filter(pk__in=ids).values_list('id', client_field)
        by_pk = {pk: client_id for pk, client_id in rows if client_id}
        for e in bucket:
            try:
                oid = int(e.object_id)
            except (TypeError, ValueError):
                continue
            if oid in by_pk:
                resolved[e.id] = by_pk[oid]

    _map_fk(('clients', 'casenote'), CaseNote)
    _map_fk(('clients', 'document'), Document)
    _map_fk(('clients', 'pitstopapplication'), PitStopApplication)
    _map_fk(('clients', 'classenrollment'), ClassEnrollment)
    return resolved


@api_view(['GET'])
@authentication_classes([StaffSessionAuthentication])
@permission_classes([IsAuthenticated])
def dashboard_activity_feed(request):
    """
    Recent system changes, sourced from Django admin's built-in LogEntry.

    Caveat (surfaced to the frontend, not hidden): this only captures actions
    taken inside the /admin/ panel. Staff SPA, public intake, kiosk, and API
    writes are NOT logged here — there is no app-wide audit log today.
    """
    err = _staff_guard(request)
    if err:
        return err

    limit = min(int(request.GET.get('limit') or 15), 50)
    action_labels = {1: 'Added', 2: 'Changed', 3: 'Deleted'}
    entries = list(
        LogEntry.objects.select_related('user', 'content_type')
        .order_by('-action_time')[:limit]
    )
    client_ids = _client_ids_for_log_entries(entries)
    data = [
        {
            'id': e.id,
            'actor': e.user.get_full_name() or e.user.username if e.user_id else 'Unknown',
            'action': action_labels.get(e.action_flag, 'Changed'),
            'model': e.content_type.name if e.content_type_id else '',
            'object_repr': e.object_repr,
            'change_message': e.get_change_message(),
            'action_time': e.action_time,
            'client_id': client_ids.get(e.id),
        }
        for e in entries
    ]
    return Response({
        'results': data,
        'source': 'admin_log_entry',
        'caveat': 'Admin panel activity only — Staff SPA, API, and kiosk changes are not captured.',
    })


@api_view(['GET'])
@authentication_classes([StaffSessionAuthentication])
@permission_classes([IsAuthenticated])
def dashboard_usage_stats(request):
    """Lightweight usage stats, sourced from existing timestamps (no second logging system)."""
    err = _staff_guard(request)
    if err:
        return err

    now = timezone.now()
    since_7d = now - timedelta(days=7)
    since_30d = now - timedelta(days=30)

    data = {
        'total_active_clients': Client.objects.filter(status='active').count(),
        'clients_updated_7d': Client.objects.filter(updated_at__gte=since_7d).count(),
        'clients_updated_30d': Client.objects.filter(updated_at__gte=since_30d).count(),
        'documents_uploaded_7d': Document.objects.filter(created_at__gte=since_7d).count(),
        'documents_uploaded_30d': Document.objects.filter(created_at__gte=since_30d).count(),
        'staff_active_7d': User.objects.filter(is_staff=True, last_login__gte=since_7d).count(),
        'staff_active_30d': User.objects.filter(is_staff=True, last_login__gte=since_30d).count(),
    }
    return Response(data)


@api_view(['GET'])
@authentication_classes([StaffSessionAuthentication])
@permission_classes([IsAuthenticated])
def dashboard_document_types(request):
    """Document type choices for the upload dropdown — reused from Document model, no drift."""
    err = _staff_guard(request)
    if err:
        return err

    return Response({
        'results': [{'value': value, 'label': label} for value, label in Document.DOC_TYPE_CHOICES]
    })


def _compress_image_if_needed(upload):
    """
    Conservative image compression via Pillow.

    Only resizes if the image is wider than IMAGE_MAX_DIMENSION; always re-saves
    at quality=85. Non-image files (PDFs, docs) pass through unchanged — no PDF
    compression library is installed.
    """
    name = (getattr(upload, 'name', '') or '').strip()
    ext = Path(name).suffix.lower()
    if ext not in COMPRESSIBLE_IMAGE_EXTENSIONS:
        return upload

    try:
        from PIL import Image
    except ImportError:
        return upload

    try:
        upload.seek(0)
        image = Image.open(upload)
        image.load()

        if image.mode in ('RGBA', 'P') and ext in ('.jpg', '.jpeg'):
            image = image.convert('RGB')

        width, height = image.size
        if width > IMAGE_MAX_DIMENSION:
            ratio = IMAGE_MAX_DIMENSION / float(width)
            image = image.resize((IMAGE_MAX_DIMENSION, int(height * ratio)), Image.LANCZOS)

        buffer = io.BytesIO()
        save_format = 'JPEG' if ext in ('.jpg', '.jpeg') else image.format or 'PNG'
        save_kwargs = {'quality': IMAGE_JPEG_QUALITY, 'optimize': True} if save_format == 'JPEG' else {'optimize': True}
        image.save(buffer, format=save_format, **save_kwargs)
        buffer.seek(0)
        return ContentFile(buffer.read(), name=name)
    except Exception as exc:
        logger.warning('Dashboard upload: image compression skipped for %s: %s', name, exc)
        try:
            upload.seek(0)
        except Exception:
            pass
        return upload


@api_view(['POST'])
@authentication_classes([StaffSessionAuthentication])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def dashboard_document_upload(request):
    """Document Upload Module: client + doc_type (required) + file, with image compression."""
    err = _staff_guard(request)
    if err:
        return err

    client_id = request.data.get('client_id')
    doc_type = (request.data.get('doc_type') or '').strip()
    upload = request.FILES.get('file')

    if not client_id:
        return Response({'client_id': ['Select a client.']}, status=status.HTTP_400_BAD_REQUEST)
    valid_doc_types = {value for value, _ in Document.DOC_TYPE_CHOICES}
    if not doc_type or doc_type not in valid_doc_types:
        return Response({'doc_type': ['Select a valid document type.']}, status=status.HTTP_400_BAD_REQUEST)
    if not upload:
        return Response({'file': ['Choose a file to upload.']}, status=status.HTTP_400_BAD_REQUEST)

    try:
        client = Client.objects.get(pk=client_id)
    except Client.DoesNotExist:
        return Response({'client_id': ['Client not found.']}, status=status.HTTP_404_NOT_FOUND)

    validation_error = _validate_uploaded_file(
        upload,
        allowed_extensions=ALLOWED_SUPPORTING_DOC_EXTENSIONS,
        max_bytes=MAX_SUPPORTING_DOC_UPLOAD_BYTES,
        label='Document',
    )
    if validation_error:
        return Response({'file': [validation_error]}, status=status.HTTP_400_BAD_REQUEST)

    stored_file = _compress_image_if_needed(upload)
    try:
        stored_file.name = f"clients/{client.pk}/{doc_type}/{upload.name}"
    except Exception:
        pass

    doc_type_label = dict(Document.DOC_TYPE_CHOICES).get(doc_type, doc_type)
    document = Document.objects.create(
        client=client,
        title=doc_type_label,
        doc_type=doc_type,
        file=stored_file,
        uploaded_by=staff_display_name(request.user),
    )
    return Response(
        {
            'message': f'Uploaded {doc_type_label} for {client.full_name}.',
            'document': {
                'id': document.id,
                'client_id': client.id,
                'doc_type': document.doc_type,
                'title': document.title,
                'created_at': document.created_at,
            },
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(['POST'])
@authentication_classes([StaffSessionAuthentication])
@permission_classes([IsAuthenticated])
def staff_feedback_submit(request):
    """
    Backward-compatible endpoint: creates a StaffTicket (open, P2).
    Prefer POST /api/staff/tickets/ for full ticket fields + attachments.
    """
    err = _staff_guard(request)
    if err:
        return err

    from .models_extensions import StaffTicket

    message = (request.data.get('message') or request.data.get('description') or '').strip()
    if not message:
        return Response({'message': ['Enter your feedback before submitting.']}, status=status.HTTP_400_BAD_REQUEST)
    if len(message) > 4000:
        return Response({'message': ['Keep feedback under 4000 characters.']}, status=status.HTTP_400_BAD_REQUEST)

    title = (request.data.get('title') or '').strip() or (message[:80] + ('…' if len(message) > 80 else ''))
    ticket = StaffTicket.objects.create(
        title=title[:200],
        description=message,
        priority=request.data.get('priority') or 'p2',
        submitted_by=request.user,
    )
    return Response(
        {'message': 'Ticket created.', 'id': ticket.id},
        status=status.HTTP_201_CREATED,
    )
