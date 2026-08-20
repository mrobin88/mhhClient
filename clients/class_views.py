"""
Staff API for Classes & Trainings scheduling — creating classes, generating/adding
sessions, roster (enroll/unenroll/attendance), and a client's own class history.

This is the staff-friendly surface so day-to-day class management (adding a new
class, scheduling more sessions, marking who showed up) never requires touching
Django admin or a code change — only admin is needed for rare edits like deleting
or renaming something.

Session-authenticated, staff-only, single-tenant.
"""
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .dashboard_views import _staff_guard
from .models import Client
from .models_classes import ClassEnrollment, ClassSession, ClassTemplate
from .staff_auth import StaffSessionAuthentication
from .staff_utils import staff_display_name

CATEGORY_VALUES = {value for value, _ in ClassTemplate.CATEGORY_CHOICES}
RECURRENCE_VALUES = {value for value, _ in ClassTemplate.RECURRENCE_CHOICES}
WEEKDAY_VALUES = {value for value, _ in ClassTemplate.WEEKDAY_CHOICES}
WEEK_OF_MONTH_VALUES = {value for value, _ in ClassTemplate.WEEK_OF_MONTH_CHOICES}
ENROLLMENT_STATUS_VALUES = {value for value, _ in ClassEnrollment.STATUS_CHOICES}
SESSION_STATUS_VALUES = {value for value, _ in ClassSession.STATUS_CHOICES}


def _template_summary(template):
    return {
        'id': template.id,
        'name': template.name,
        'category': template.category,
        'category_display': template.get_category_display(),
        'description': template.description,
        'location': template.location,
        'facilitator': template.facilitator,
        'capacity': template.capacity,
        'start_time': template.start_time,
        'end_time': template.end_time,
        'recurrence': template.recurrence,
        'recurrence_weekday': template.recurrence_weekday,
        'recurrence_week_of_month': template.recurrence_week_of_month,
        'recurrence_summary': template.recurrence_summary,
        'is_active': template.is_active,
        'upcoming_sessions_count': getattr(template, '_upcoming_count', None),
    }


def _session_summary(session):
    return {
        'id': session.id,
        'template_id': session.template_id,
        'template_name': session.template.name,
        'category': session.template.category,
        'category_display': session.template.get_category_display(),
        'session_date': session.session_date,
        'start_time': session.start_time,
        'end_time': session.end_time,
        'location': session.location,
        'facilitator': session.facilitator,
        'capacity': session.capacity,
        'enrolled_count': getattr(session, '_enrolled_count', None) or session.enrolled_count,
        'spots_remaining': session.capacity - (getattr(session, '_enrolled_count', None) or session.enrolled_count),
        'status': session.status,
    }


@api_view(['GET'])
@authentication_classes([StaffSessionAuthentication])
@permission_classes([IsAuthenticated])
def staff_upcoming_classes(request):
    """
    Upcoming scheduled class sessions — powers the "add to class" selector on the
    Client Detail page and the Upcoming Classes card on the Staff Dashboard.
    """
    err = _staff_guard(request)
    if err:
        return err

    days = min(int(request.GET.get('days') or 60), 180)
    today = timezone.localdate()
    horizon = today + timedelta(days=days)

    sessions = (
        ClassSession.objects.filter(
            status='scheduled', session_date__gte=today, session_date__lte=horizon
        )
        .select_related('template')
        .annotate(
            _enrolled_count=Count(
                'enrollments', filter=Q(enrollments__status__in=['registered', 'attended'])
            )
        )
        .order_by('session_date', 'start_time')
    )

    category = (request.GET.get('category') or '').strip()
    if category:
        sessions = sessions.filter(template__category=category)

    return Response({'results': [_session_summary(s) for s in sessions]})


@api_view(['GET'])
@authentication_classes([StaffSessionAuthentication])
@permission_classes([IsAuthenticated])
def staff_class_roster(request, session_id):
    """Roster for a single class session — used by the Dashboard's expandable roster view."""
    err = _staff_guard(request)
    if err:
        return err

    try:
        session = (
            ClassSession.objects.select_related('template')
            .annotate(
                _enrolled_count=Count(
                    'enrollments', filter=Q(enrollments__status__in=['registered', 'attended'])
                )
            )
            .get(pk=session_id)
        )
    except ClassSession.DoesNotExist:
        return Response({'error': 'Class session not found.'}, status=status.HTTP_404_NOT_FOUND)

    enrollments = (
        session.enrollments.select_related('client')
        .exclude(status='cancelled')
        .order_by('client__last_name', 'client__first_name')
    )
    return Response({
        'session': _session_summary(session),
        'roster': [
            {
                'enrollment_id': e.id,
                'client_id': e.client_id,
                'client_full_name': e.client.full_name,
                'client_phone': e.client.phone,
                'status': e.status,
                'status_display': e.get_status_display(),
                'registered_by': e.registered_by,
                'registered_at': e.registered_at,
            }
            for e in enrollments
        ],
    })


@api_view(['GET'])
@authentication_classes([StaffSessionAuthentication])
@permission_classes([IsAuthenticated])
def staff_client_classes(request, pk):
    """A single client's class enrollments — for display on the Client Detail page."""
    err = _staff_guard(request)
    if err:
        return err

    try:
        client = Client.objects.get(pk=pk)
    except Client.DoesNotExist:
        return Response({'error': 'Client not found.'}, status=status.HTTP_404_NOT_FOUND)

    enrollments = (
        client.class_enrollments.select_related('session', 'session__template')
        .exclude(status='cancelled')
        .order_by('-session__session_date')
    )
    return Response({
        'results': [
            {
                'enrollment_id': e.id,
                'session_id': e.session_id,
                'template_name': e.session.template.name,
                'category': e.session.template.category,
                'category_display': e.session.template.get_category_display(),
                'session_date': e.session.session_date,
                'start_time': e.session.start_time,
                'end_time': e.session.end_time,
                'location': e.session.location,
                'status': e.status,
                'status_display': e.get_status_display(),
            }
            for e in enrollments
        ]
    })


@api_view(['POST'])
@authentication_classes([StaffSessionAuthentication])
@permission_classes([IsAuthenticated])
def staff_class_enroll(request, session_id):
    """Add a client to a class session's roster (from the Client Detail page or Dashboard)."""
    err = _staff_guard(request)
    if err:
        return err

    client_id = request.data.get('client_id')
    if not client_id:
        return Response({'client_id': ['Select a client.']}, status=status.HTTP_400_BAD_REQUEST)

    try:
        session = (
            ClassSession.objects.select_related('template')
            .annotate(
                _enrolled_count=Count(
                    'enrollments', filter=Q(enrollments__status__in=['registered', 'attended'])
                )
            )
            .get(pk=session_id)
        )
    except ClassSession.DoesNotExist:
        return Response({'error': 'Class session not found.'}, status=status.HTTP_404_NOT_FOUND)

    try:
        client = Client.objects.get(pk=client_id)
    except Client.DoesNotExist:
        return Response({'client_id': ['Client not found.']}, status=status.HTTP_404_NOT_FOUND)

    existing = ClassEnrollment.objects.filter(session=session, client=client).first()
    if existing and existing.status in ('registered', 'attended'):
        return Response(
            {'error': f'{client.full_name} is already on this roster.'}, status=status.HTTP_400_BAD_REQUEST
        )

    if not existing and session._enrolled_count >= session.capacity:
        return Response(
            {'error': 'This class is full. Choose a different session or increase capacity in admin.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if existing:
        existing.status = 'registered'
        existing.registered_by = staff_display_name(request.user)
        existing.save(update_fields=['status', 'registered_by'])
        enrollment = existing
    else:
        enrollment = ClassEnrollment.objects.create(
            session=session, client=client, registered_by=staff_display_name(request.user)
        )

    from .notifications import send_class_confirmation

    text_outcome, text_detail = send_class_confirmation(client, session, enrollment)
    message = f'Added {client.full_name} to {session.template.name} on {session.session_date}.'
    if text_outcome == 'sent':
        message = f'{message} {text_detail}'

    return Response(
        {
            'message': message,
            'enrollment_id': enrollment.id,
            'text_outcome': text_outcome,
            # Staff only need telling when a text was expected and did not go out.
            'text_warning': text_detail if text_outcome == 'failed' else '',
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(['GET'])
@authentication_classes([StaffSessionAuthentication])
@permission_classes([IsAuthenticated])
def staff_class_text_preview(request, session_id):
    """
    The confirmation text this client would get for this class.

    Staff sign people up over the phone or at the front desk, so they need to
    see the exact message before they commit — and to know when no text is
    going out so they can say the date and time out loud instead.
    """
    err = _staff_guard(request)
    if err:
        return err

    client_id = request.query_params.get('client_id')
    if not client_id:
        return Response({'client_id': ['Select a client.']}, status=status.HTTP_400_BAD_REQUEST)

    try:
        session = ClassSession.objects.select_related('template').get(pk=session_id)
    except ClassSession.DoesNotExist:
        return Response({'error': 'Class session not found.'}, status=status.HTTP_404_NOT_FOUND)

    try:
        client = Client.objects.get(pk=client_id)
    except (Client.DoesNotExist, ValueError):
        return Response({'client_id': ['Client not found.']}, status=status.HTTP_404_NOT_FOUND)

    from .notifications import class_confirmation_preview

    will_send, reason, body = class_confirmation_preview(client, session)
    return Response(
        {
            'will_send': will_send,
            'reason': reason,
            'to_phone': client.phone or '',
            'body': body,
        }
    )


@api_view(['POST'])
@authentication_classes([StaffSessionAuthentication])
@permission_classes([IsAuthenticated])
def staff_class_unenroll(request, session_id):
    """Remove a client from a class session's roster (soft — keeps the record, marks cancelled)."""
    err = _staff_guard(request)
    if err:
        return err

    client_id = request.data.get('client_id')
    if not client_id:
        return Response({'client_id': ['Select a client.']}, status=status.HTTP_400_BAD_REQUEST)

    enrollment = ClassEnrollment.objects.filter(session_id=session_id, client_id=client_id).first()
    if not enrollment:
        return Response({'error': 'Enrollment not found.'}, status=status.HTTP_404_NOT_FOUND)

    enrollment.status = 'cancelled'
    enrollment.save(update_fields=['status'])
    return Response({'message': 'Removed from class.'})


@api_view(['GET'])
@authentication_classes([StaffSessionAuthentication])
@permission_classes([IsAuthenticated])
def staff_class_templates(request):
    """List classes/trainings for the Manage Classes page — no admin needed."""
    err = _staff_guard(request)
    if err:
        return err

    today = timezone.localdate()
    templates = (
        ClassTemplate.objects.all()
        .annotate(
            _upcoming_count=Count(
                'sessions',
                filter=Q(sessions__status='scheduled', sessions__session_date__gte=today),
            )
        )
        .order_by('-is_active', 'name')
    )
    return Response({'results': [_template_summary(t) for t in templates]})


@api_view(['PATCH'])
@authentication_classes([StaffSessionAuthentication])
@permission_classes([IsAuthenticated])
def staff_class_template_update(request, template_id):
    """Edit or deactivate a class/JRT template without deleting its history."""
    err = _staff_guard(request)
    if err:
        return err
    try:
        template = ClassTemplate.objects.get(pk=template_id)
    except ClassTemplate.DoesNotExist:
        return Response({'error': 'Class not found.'}, status=status.HTTP_404_NOT_FOUND)

    text_fields = ('name', 'description', 'location', 'facilitator')
    for field in text_fields:
        if field in request.data:
            setattr(template, field, str(request.data.get(field) or '').strip())

    for field in ('category', 'recurrence'):
        if field in request.data:
            setattr(template, field, str(request.data.get(field) or '').strip())
    for field in ('start_time', 'end_time'):
        if field in request.data and request.data.get(field):
            setattr(template, field, request.data[field])
    if 'is_active' in request.data:
        active_value = request.data.get('is_active')
        template.is_active = active_value is True or str(active_value).lower() in ('1', 'true', 'yes')

    errors = {}
    if not template.name:
        errors['name'] = ['Enter a class name.']
    if template.category not in CATEGORY_VALUES:
        errors['category'] = ['Choose a valid category.']
    if template.recurrence not in RECURRENCE_VALUES:
        errors['recurrence'] = ['Choose a valid recurrence.']
    if 'capacity' in request.data:
        try:
            template.capacity = int(request.data['capacity'])
            if template.capacity < 1:
                raise ValueError
        except (TypeError, ValueError):
            errors['capacity'] = ['Capacity must be a positive number.']

    def _optional_int(field):
        value = request.data.get(field)
        if value in (None, ''):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    if 'recurrence_weekday' in request.data:
        template.recurrence_weekday = _optional_int('recurrence_weekday')
    if 'recurrence_week_of_month' in request.data:
        template.recurrence_week_of_month = _optional_int('recurrence_week_of_month')
    if template.recurrence == 'none':
        template.recurrence_weekday = None
        template.recurrence_week_of_month = None
    elif template.recurrence_weekday not in WEEKDAY_VALUES:
        errors['recurrence_weekday'] = ['Pick a day of the week.']
    if template.recurrence == 'monthly':
        if template.recurrence_week_of_month not in WEEK_OF_MONTH_VALUES:
            errors['recurrence_week_of_month'] = ['Pick which week of the month.']
    else:
        template.recurrence_week_of_month = None

    if errors:
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)
    try:
        template.full_clean()
    except ValidationError as exc:
        return Response(exc.message_dict, status=status.HTTP_400_BAD_REQUEST)
    template.save()
    return Response({'message': f'Updated "{template.name}".', 'template': _template_summary(template)})


@api_view(['POST'])
@authentication_classes([StaffSessionAuthentication])
@permission_classes([IsAuthenticated])
def staff_class_template_create(request):
    """
    Create a new class/training from the dashboard. Recurring classes get their
    first batch of sessions generated immediately; one-time classes require a
    session_date so the single session is created in the same step.
    """
    err = _staff_guard(request)
    if err:
        return err

    data = request.data
    name = str(data.get('name') or '').strip()
    category = str(data.get('category') or 'training').strip()
    recurrence = str(data.get('recurrence') or 'none').strip()
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    session_date = str(data.get('session_date') or '').strip()

    errors = {}
    if not name:
        errors['name'] = ['Enter a class name.']
    if category not in CATEGORY_VALUES:
        errors['category'] = ['Choose a valid category.']
    if recurrence not in RECURRENCE_VALUES:
        errors['recurrence'] = ['Choose a valid recurrence.']
    if not start_time:
        errors['start_time'] = ['Enter a start time.']
    if not end_time:
        errors['end_time'] = ['Enter an end time.']
    if recurrence == 'none' and not session_date:
        errors['session_date'] = ['Pick a date — one-time classes need a single date.']

    try:
        capacity = int(data.get('capacity') or 20)
        if capacity < 1:
            raise ValueError('capacity must be positive')
    except (TypeError, ValueError):
        errors['capacity'] = ['Capacity must be a positive number.']
        capacity = 20

    def _clean_int(value):
        if value in (None, ''):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    recurrence_weekday = _clean_int(data.get('recurrence_weekday'))
    recurrence_week_of_month = _clean_int(data.get('recurrence_week_of_month'))
    if recurrence in ('weekly', 'monthly') and recurrence_weekday not in WEEKDAY_VALUES:
        errors['recurrence_weekday'] = ['Pick a day of the week.']
    if recurrence == 'monthly' and recurrence_week_of_month not in WEEK_OF_MONTH_VALUES:
        errors['recurrence_week_of_month'] = ['Pick which week of the month.']

    if errors:
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)

    template = ClassTemplate(
        name=name,
        category=category,
        description=str(data.get('description') or '').strip(),
        location=str(data.get('location') or '').strip(),
        facilitator=str(data.get('facilitator') or '').strip(),
        capacity=capacity,
        start_time=start_time,
        end_time=end_time,
        recurrence=recurrence,
        recurrence_weekday=recurrence_weekday if recurrence != 'none' else None,
        recurrence_week_of_month=recurrence_week_of_month if recurrence == 'monthly' else None,
    )
    try:
        template.full_clean()
    except ValidationError as exc:
        return Response(exc.message_dict, status=status.HTTP_400_BAD_REQUEST)
    template.save()

    sessions_created = 0
    if recurrence != 'none':
        sessions_created = len(template.generate_upcoming_sessions(horizon_days=60))
    elif session_date:
        ClassSession.objects.create(
            template=template,
            session_date=session_date,
            start_time=template.start_time,
            end_time=template.end_time,
            location=template.location,
            facilitator=template.facilitator,
            capacity=template.capacity,
        )
        sessions_created = 1

    return Response(
        {
            'message': f'Created "{template.name}" — {sessions_created} session(s) scheduled.',
            'template': _template_summary(template),
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(['GET'])
@authentication_classes([StaffSessionAuthentication])
@permission_classes([IsAuthenticated])
def staff_class_template_sessions(request, template_id):
    """A single class's upcoming sessions — for the expandable row on Manage Classes."""
    err = _staff_guard(request)
    if err:
        return err

    try:
        template = ClassTemplate.objects.get(pk=template_id)
    except ClassTemplate.DoesNotExist:
        return Response({'error': 'Class not found.'}, status=status.HTTP_404_NOT_FOUND)

    today = timezone.localdate()
    sessions = (
        template.sessions.filter(session_date__gte=today)
        .select_related('template')
        .annotate(
            _enrolled_count=Count(
                'enrollments', filter=Q(enrollments__status__in=['registered', 'attended'])
            )
        )
        .order_by('session_date', 'start_time')
    )
    return Response({'results': [_session_summary(s) for s in sessions]})


@api_view(['POST'])
@authentication_classes([StaffSessionAuthentication])
@permission_classes([IsAuthenticated])
def staff_class_template_generate_sessions(request, template_id):
    """Extend a recurring class's schedule by another 60 days, on demand."""
    err = _staff_guard(request)
    if err:
        return err

    try:
        template = ClassTemplate.objects.get(pk=template_id)
    except ClassTemplate.DoesNotExist:
        return Response({'error': 'Class not found.'}, status=status.HTTP_404_NOT_FOUND)

    if template.recurrence == 'none':
        return Response(
            {'error': "One-time classes don't auto-generate sessions — add a specific date instead."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    created = template.generate_upcoming_sessions(horizon_days=60)
    if created:
        message = f'Added {len(created)} new session(s) through {created[-1].session_date}.'
    else:
        message = 'Already up to date — no new sessions needed yet.'
    return Response({'message': message, 'created_count': len(created)})


@api_view(['POST'])
@authentication_classes([StaffSessionAuthentication])
@permission_classes([IsAuthenticated])
def staff_class_session_create(request):
    """Add a specific one-off date to any class — recurring or one-time."""
    err = _staff_guard(request)
    if err:
        return err

    template_id = request.data.get('template_id')
    session_date = str(request.data.get('session_date') or '').strip()
    if not template_id or not session_date:
        return Response({'error': 'Choose a class and a date.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        template = ClassTemplate.objects.get(pk=template_id)
    except ClassTemplate.DoesNotExist:
        return Response({'error': 'Class not found.'}, status=status.HTTP_404_NOT_FOUND)

    if template.sessions.filter(session_date=session_date).exists():
        return Response({'error': 'A session already exists on that date.'}, status=status.HTTP_400_BAD_REQUEST)

    session = ClassSession.objects.create(
        template=template,
        session_date=session_date,
        start_time=template.start_time,
        end_time=template.end_time,
        location=template.location,
        facilitator=template.facilitator,
        capacity=template.capacity,
    )
    return Response(
        {'message': f'Added {template.name} on {session_date}.', 'session': _session_summary(session)},
        status=status.HTTP_201_CREATED,
    )


@api_view(['PATCH'])
@authentication_classes([StaffSessionAuthentication])
@permission_classes([IsAuthenticated])
def staff_class_session_update(request, session_id):
    """Edit, complete, or cancel a dated class session while preserving its roster."""
    err = _staff_guard(request)
    if err:
        return err
    try:
        session = ClassSession.objects.select_related('template').get(pk=session_id)
    except ClassSession.DoesNotExist:
        return Response({'error': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)

    for field in ('session_date', 'start_time', 'end_time', 'location', 'facilitator', 'notes'):
        if field in request.data:
            value = request.data.get(field)
            if field in ('location', 'facilitator', 'notes'):
                value = str(value or '').strip()
            setattr(session, field, value)

    errors = {}
    if 'status' in request.data:
        new_status = str(request.data.get('status') or '').strip()
        if new_status not in SESSION_STATUS_VALUES:
            errors['status'] = ['Choose a valid session status.']
        else:
            session.status = new_status
    if 'capacity' in request.data:
        try:
            capacity = int(request.data['capacity'])
            if capacity < 1:
                raise ValueError
            if capacity < session.enrolled_count:
                errors['capacity'] = [
                    f'Capacity cannot be below the {session.enrolled_count} currently enrolled.'
                ]
            else:
                session.capacity = capacity
        except (TypeError, ValueError):
            errors['capacity'] = ['Capacity must be a positive number.']
    if (
        session.session_date
        and session.template.sessions.exclude(pk=session.pk)
        .filter(session_date=session.session_date)
        .exists()
    ):
        errors['session_date'] = ['This class already has a session on that date.']
    if errors:
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)
    try:
        session.full_clean()
    except ValidationError as exc:
        return Response(exc.message_dict, status=status.HTTP_400_BAD_REQUEST)
    session.save()
    return Response({'message': 'Session updated.', 'session': _session_summary(session)})


@api_view(['POST'])
@authentication_classes([StaffSessionAuthentication])
@permission_classes([IsAuthenticated])
def staff_class_enrollment_status(request, enrollment_id):
    """Mark attendance (attended/no-show) or otherwise update one roster entry's status."""
    err = _staff_guard(request)
    if err:
        return err

    new_status = str(request.data.get('status') or '').strip()
    if new_status not in ENROLLMENT_STATUS_VALUES:
        return Response({'status': ['Choose a valid status.']}, status=status.HTTP_400_BAD_REQUEST)

    try:
        enrollment = ClassEnrollment.objects.get(pk=enrollment_id)
    except ClassEnrollment.DoesNotExist:
        return Response({'error': 'Enrollment not found.'}, status=status.HTTP_404_NOT_FOUND)

    enrollment.status = new_status
    enrollment.save(update_fields=['status'])
    return Response({'message': 'Updated.', 'status': enrollment.status, 'status_display': enrollment.get_status_display()})
