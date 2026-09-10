"""Staff review of Pit Stop applications — the digital paper stack."""
from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .dashboard_views import _staff_guard
from .models import PitStopApplication
from .staff_auth import StaffSessionAuthentication
from .staff_utils import staff_display_name

REVIEW_STATUSES = {value for value, _ in PitStopApplication.REVIEW_STATUS_CHOICES}


def _resume_path(app):
    client = app.client
    if client.resume:
        return f'/api/clients/{client.pk}/resume/'
    doc = (
        client.documents.filter(doc_type='resume')
        .exclude(file='')
        .order_by('-created_at')
        .first()
    )
    if doc:
        return f'/api/documents/{doc.pk}/download/'
    return ''


def _application_payload(app, *, detail=False):
    client = app.client
    data = {
        'id': app.pk,
        'client_id': client.pk,
        'full_name': client.full_name,
        'first_name': client.first_name,
        'middle_name': client.middle_name or '',
        'last_name': client.last_name,
        'phone': client.phone or '',
        'email': client.email or '',
        'address': client.address or '',
        'city': client.city or '',
        'state': client.state or '',
        'zip_code': client.zip_code or '',
        'age': app.applicant_age,
        'area_code': app.area_code,
        'has_resume': app.has_resume,
        'resume_url': _resume_path(app),
        'review_status': app.review_status,
        'review_status_display': app.get_review_status_display(),
        'position_applied_for': app.position_applied_for,
        'available_start_date': app.available_start_date,
        'employment_desired': app.employment_desired or [],
        'open_availability': bool(app.available_days_list),
        'created_at': app.created_at,
        'pit_stop_stage': client.pit_stop_stage,
        'pit_stop_stage_display': client.get_pit_stop_stage_display(),
    }
    if not detail:
        return data

    data.update(
        {
            'can_work_us': app.can_work_us,
            'is_veteran': app.is_veteran,
            'weekly_schedule': app.weekly_schedule or {},
            'available_days': app.available_days_list,
            'employment_history': app.employment_history or [],
            'high_school_name': app.high_school_name,
            'high_school_city': app.high_school_city,
            'high_school_state': app.high_school_state,
            'post_secondary_name': app.post_secondary_name,
            'post_secondary_city': app.post_secondary_city,
            'post_secondary_state': app.post_secondary_state,
            'education_history': app.education_history or '',
            'what_is_pit_stop': app.what_is_pit_stop,
            'why_participate': app.why_participate,
            'goals_after_program': app.goals_after_program,
            'how_program_supports_goals': app.how_program_supports_goals,
            'signature_name': app.signature_name,
            'signed_on': app.signed_on,
            'interviewed_on': app.interviewed_on,
            'review_notes': app.review_notes,
            'reviewed_by': app.reviewed_by,
            'review_updated_at': app.review_updated_at,
        }
    )
    return data


@api_view(['GET'])
@authentication_classes([StaffSessionAuthentication])
@permission_classes([IsAuthenticated])
def staff_pitstop_applications(request):
    err = _staff_guard(request)
    if err:
        return err

    qs = PitStopApplication.objects.select_related('client').order_by('-created_at')
    status_filter = (request.GET.get('status') or '').strip()
    if status_filter and status_filter in REVIEW_STATUSES:
        qs = qs.filter(review_status=status_filter)

    search = (request.GET.get('q') or '').strip()
    if search:
        qs = qs.filter(
            Q(client__first_name__icontains=search)
            | Q(client__last_name__icontains=search)
            | Q(client__phone__icontains=search)
            | Q(position_applied_for__icontains=search)
        )

    resume = (request.GET.get('resume') or '').strip().lower()
    if resume == 'yes':
        qs = [app for app in qs if app.has_resume]
        total = len(qs)
        results = [_application_payload(app) for app in qs[:80]]
        return Response({'results': results, 'total': total, 'statuses': _status_choices()})
    if resume == 'no':
        qs = [app for app in qs if not app.has_resume]
        total = len(qs)
        results = [_application_payload(app) for app in qs[:80]]
        return Response({'results': results, 'total': total, 'statuses': _status_choices()})

    total = qs.count()
    results = [_application_payload(app) for app in qs[:80]]
    return Response({'results': results, 'total': total, 'statuses': _status_choices()})


def _status_choices():
    return [
        {'value': value, 'label': label}
        for value, label in PitStopApplication.REVIEW_STATUS_CHOICES
    ]


@api_view(['GET', 'PATCH'])
@authentication_classes([StaffSessionAuthentication])
@permission_classes([IsAuthenticated])
def staff_pitstop_application_detail(request, pk):
    err = _staff_guard(request)
    if err:
        return err

    try:
        app = PitStopApplication.objects.select_related('client').get(pk=pk)
    except PitStopApplication.DoesNotExist:
        return Response({'error': 'Application not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(_application_payload(app, detail=True))

    from django.utils import timezone

    changed = False
    review_status = request.data.get('review_status')
    if review_status is not None:
        if review_status not in REVIEW_STATUSES:
            return Response({'error': 'Invalid review status.'}, status=status.HTTP_400_BAD_REQUEST)
        app.review_status = review_status
        changed = True

    if 'interviewed_on' in request.data:
        raw = request.data.get('interviewed_on') or None
        app.interviewed_on = raw or None
        changed = True

    if 'review_notes' in request.data:
        app.review_notes = (request.data.get('review_notes') or '').strip()
        changed = True

    if changed:
        app.reviewed_by = staff_display_name(request.user)
        app.review_updated_at = timezone.now()
        app.save()

    return Response(_application_payload(app, detail=True))
