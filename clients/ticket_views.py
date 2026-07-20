"""Staff ticket / feedback issue tracking APIs."""
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes, parser_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .dashboard_views import _compress_image_if_needed, _staff_guard
from .models_extensions import StaffTicket, StaffTicketAttachment
from .staff_auth import StaffSessionAuthentication
from .staff_utils import staff_display_name
from .storage import generate_document_sas_url

User = get_user_model()

CLOSED_STATUSES = {StaffTicket.STATUS_RESOLVED, StaffTicket.STATUS_CLOSED}
VALID_TAGS = {value for value, _ in StaffTicket.TAG_CHOICES}
VALID_PRIORITIES = {value for value, _ in StaffTicket.PRIORITY_CHOICES}
VALID_STATUSES = {value for value, _ in StaffTicket.STATUS_CHOICES}
VALID_RESOLUTIONS = {value for value, _ in StaffTicket.RESOLUTION_CHOICES}


def _user_label(user):
    if not user:
        return None
    return staff_display_name(user) or user.get_username()


def _attachment_payload(att):
    url = ''
    try:
        url = generate_document_sas_url(att.file.name) if att.file else ''
    except Exception:
        try:
            url = att.file.url if att.file else ''
        except Exception:
            url = ''
    return {
        'id': att.id,
        'original_name': att.original_name or (att.file.name.split('/')[-1] if att.file else ''),
        'content_type': att.content_type or '',
        'url': url,
        'created_at': att.created_at,
        'uploaded_by': _user_label(att.uploaded_by),
    }


def _ticket_payload(ticket, *, include_attachments=False):
    attachments = list(ticket.attachments.all()) if include_attachments else None
    data = {
        'id': ticket.id,
        'title': ticket.title,
        'description': ticket.description,
        'status': ticket.status,
        'status_display': ticket.get_status_display(),
        'resolution': ticket.resolution or '',
        'resolution_display': ticket.get_resolution_display() if ticket.resolution else '',
        'priority': ticket.priority,
        'priority_display': ticket.get_priority_display(),
        'tags': list(ticket.tags or []),
        'submitted_by_id': ticket.submitted_by_id,
        'submitted_by_name': _user_label(ticket.submitted_by),
        'assignee_id': ticket.assignee_id,
        'assignee_name': _user_label(ticket.assignee),
        'duplicate_of_id': ticket.duplicate_of_id,
        'created_at': ticket.created_at,
        'updated_at': ticket.updated_at,
        'resolved_at': ticket.resolved_at,
        'attachment_count': len(attachments) if attachments is not None else ticket.attachments.count(),
    }
    if include_attachments:
        data['attachments'] = [_attachment_payload(a) for a in attachments]
    return data


def _parse_tags(raw):
    if raw is None:
        return []
    if isinstance(raw, str):
        # JSON array string or comma-separated
        raw = raw.strip()
        if raw.startswith('['):
            import json
            try:
                raw = json.loads(raw)
            except json.JSONDecodeError:
                raw = [t.strip() for t in raw.strip('[]').replace('"', '').split(',') if t.strip()]
        else:
            raw = [t.strip() for t in raw.split(',') if t.strip()]
    if not isinstance(raw, (list, tuple)):
        return []
    return [t for t in raw if t in VALID_TAGS]


def _apply_ticket_updates(ticket, data, *, partial=True):
    """Apply PATCH/create fields with validation. Returns (ok, error_response)."""
    errors = {}

    if 'title' in data or not partial:
        title = (data.get('title') or '').strip()
        if not title:
            errors['title'] = ['Enter a short title.']
        elif len(title) > 200:
            errors['title'] = ['Keep the title under 200 characters.']
        else:
            ticket.title = title

    if 'description' in data or not partial:
        description = (data.get('description') or '').strip()
        if not description:
            errors['description'] = ['Describe what is needed or what went wrong.']
        elif len(description) > 8000:
            errors['description'] = ['Keep the description under 8000 characters.']
        else:
            ticket.description = description

    if 'priority' in data:
        priority = data.get('priority') or 'p2'
        if priority not in VALID_PRIORITIES:
            errors['priority'] = ['Pick a valid priority (P0–P4).']
        else:
            ticket.priority = priority

    if 'tags' in data:
        ticket.tags = _parse_tags(data.get('tags'))

    if 'assignee_id' in data:
        assignee_id = data.get('assignee_id')
        if assignee_id in (None, '', 'null'):
            ticket.assignee = None
        else:
            try:
                assignee = User.objects.get(pk=int(assignee_id), is_staff=True, is_active=True)
                ticket.assignee = assignee
            except (User.DoesNotExist, TypeError, ValueError):
                errors['assignee_id'] = ['Pick a valid staff assignee.']

    if 'duplicate_of_id' in data:
        dup_id = data.get('duplicate_of_id')
        if dup_id in (None, '', 'null'):
            ticket.duplicate_of = None
        else:
            try:
                dup = StaffTicket.objects.get(pk=int(dup_id))
                if ticket.pk and dup.pk == ticket.pk:
                    errors['duplicate_of_id'] = ['A ticket cannot be a duplicate of itself.']
                else:
                    ticket.duplicate_of = dup
            except (StaffTicket.DoesNotExist, TypeError, ValueError):
                errors['duplicate_of_id'] = ['Duplicate ticket not found.']

    new_status = ticket.status
    if 'status' in data:
        status_val = data.get('status')
        if status_val not in VALID_STATUSES:
            errors['status'] = ['Pick a valid status.']
        else:
            new_status = status_val

    new_resolution = ticket.resolution or ''
    if 'resolution' in data:
        res = data.get('resolution') or ''
        if res and res not in VALID_RESOLUTIONS:
            errors['resolution'] = ['Pick a valid resolution code.']
        else:
            new_resolution = res

    if new_status in CLOSED_STATUSES and not new_resolution:
        errors['resolution'] = ['Choose a resolution code when marking Resolved or Closed.']

    if new_status not in CLOSED_STATUSES:
        new_resolution = ''

    if errors:
        return False, Response(errors, status=status.HTTP_400_BAD_REQUEST)

    ticket.status = new_status
    ticket.resolution = new_resolution
    if new_status in CLOSED_STATUSES:
        if not ticket.resolved_at:
            ticket.resolved_at = timezone.now()
    else:
        ticket.resolved_at = None

    return True, None


def _collect_uploads(request):
    files = []
    for key in ('attachments', 'files', 'file', 'screenshot'):
        for f in request.FILES.getlist(key):
            files.append(f)
    # Also accept attachments[] style
    for key, f in request.FILES.items():
        if key.startswith('attachments') and f not in files:
            files.append(f)
    return files


@api_view(['GET', 'POST'])
@authentication_classes([StaffSessionAuthentication])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def staff_tickets(request):
    err = _staff_guard(request)
    if err:
        return err

    if request.method == 'GET':
        scope = (request.GET.get('scope') or 'mine').strip().lower()
        qs = StaffTicket.objects.select_related('submitted_by', 'assignee').prefetch_related('attachments')
        if scope == 'mine':
            from django.db.models import Q
            qs = qs.filter(Q(submitted_by=request.user) | Q(assignee=request.user)).distinct()
        elif scope != 'all':
            return Response({'scope': ['Use scope=mine or scope=all.']}, status=status.HTTP_400_BAD_REQUEST)

        status_filter = (request.GET.get('status') or '').strip()
        if status_filter:
            if status_filter not in VALID_STATUSES:
                return Response({'status': ['Invalid status filter.']}, status=status.HTTP_400_BAD_REQUEST)
            qs = qs.filter(status=status_filter)

        limit = min(int(request.GET.get('limit') or 40), 100)
        tickets = list(qs.order_by('-updated_at')[:limit])
        return Response({
            'results': [_ticket_payload(t) for t in tickets],
            'meta': {
                'statuses': [{'value': v, 'label': l} for v, l in StaffTicket.STATUS_CHOICES],
                'resolutions': [{'value': v, 'label': l} for v, l in StaffTicket.RESOLUTION_CHOICES],
                'priorities': [{'value': v, 'label': l} for v, l in StaffTicket.PRIORITY_CHOICES],
                'tags': [{'value': v, 'label': l} for v, l in StaffTicket.TAG_CHOICES],
            },
        })

    # POST create
    data = request.data
    ticket = StaffTicket(submitted_by=request.user, priority='p2', status=StaffTicket.STATUS_OPEN)
    ok, err_resp = _apply_ticket_updates(ticket, data, partial=False)
    if not ok:
        return err_resp
    # Default priority if missing on create
    if 'priority' not in data:
        ticket.priority = 'p2'
    ticket.save()

    for upload in _collect_uploads(request):
        stored = _compress_image_if_needed(upload)
        StaffTicketAttachment.objects.create(
            ticket=ticket,
            file=stored,
            original_name=getattr(upload, 'name', '') or '',
            content_type=getattr(upload, 'content_type', '') or '',
            uploaded_by=request.user,
        )

    ticket = StaffTicket.objects.prefetch_related('attachments').select_related(
        'submitted_by', 'assignee'
    ).get(pk=ticket.pk)
    return Response(_ticket_payload(ticket, include_attachments=True), status=status.HTTP_201_CREATED)


@api_view(['GET', 'PATCH'])
@authentication_classes([StaffSessionAuthentication])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def staff_ticket_detail(request, pk):
    err = _staff_guard(request)
    if err:
        return err

    try:
        ticket = StaffTicket.objects.select_related(
            'submitted_by', 'assignee', 'duplicate_of'
        ).prefetch_related('attachments').get(pk=pk)
    except StaffTicket.DoesNotExist:
        return Response({'detail': 'Ticket not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(_ticket_payload(ticket, include_attachments=True))

    ok, err_resp = _apply_ticket_updates(ticket, request.data, partial=True)
    if not ok:
        return err_resp
    ticket.save()
    ticket = StaffTicket.objects.select_related(
        'submitted_by', 'assignee', 'duplicate_of'
    ).prefetch_related('attachments').get(pk=ticket.pk)
    return Response(_ticket_payload(ticket, include_attachments=True))


@api_view(['POST'])
@authentication_classes([StaffSessionAuthentication])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def staff_ticket_attachments(request, pk):
    err = _staff_guard(request)
    if err:
        return err

    try:
        ticket = StaffTicket.objects.get(pk=pk)
    except StaffTicket.DoesNotExist:
        return Response({'detail': 'Ticket not found.'}, status=status.HTTP_404_NOT_FOUND)

    uploads = _collect_uploads(request)
    if not uploads:
        return Response({'file': ['Choose a screenshot or document to upload.']}, status=status.HTTP_400_BAD_REQUEST)

    created = []
    for upload in uploads:
        stored = _compress_image_if_needed(upload)
        att = StaffTicketAttachment.objects.create(
            ticket=ticket,
            file=stored,
            original_name=getattr(upload, 'name', '') or '',
            content_type=getattr(upload, 'content_type', '') or '',
            uploaded_by=request.user,
        )
        created.append(_attachment_payload(att))

    ticket.updated_at = timezone.now()
    ticket.save(update_fields=['updated_at'])
    return Response({'attachments': created}, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@authentication_classes([StaffSessionAuthentication])
@permission_classes([IsAuthenticated])
def staff_ticket_assignees(request):
    err = _staff_guard(request)
    if err:
        return err

    q = (request.GET.get('q') or '').strip()
    qs = User.objects.filter(is_staff=True, is_active=True).order_by('first_name', 'last_name', 'username')
    if q:
        from django.db.models import Q
        qs = qs.filter(
            Q(username__icontains=q)
            | Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(email__icontains=q)
        )
    results = [
        {
            'id': u.id,
            'name': staff_display_name(u) or u.get_username(),
            'username': u.get_username(),
        }
        for u in qs[:20]
    ]
    return Response({'results': results})


@api_view(['GET'])
@authentication_classes([StaffSessionAuthentication])
@permission_classes([IsAuthenticated])
def staff_ticket_meta(request):
    err = _staff_guard(request)
    if err:
        return err
    return Response({
        'statuses': [{'value': v, 'label': l} for v, l in StaffTicket.STATUS_CHOICES],
        'resolutions': [{'value': v, 'label': l} for v, l in StaffTicket.RESOLUTION_CHOICES],
        'priorities': [{'value': v, 'label': l} for v, l in StaffTicket.PRIORITY_CHOICES],
        'tags': [{'value': v, 'label': l} for v, l in StaffTicket.TAG_CHOICES],
    })
