"""
Secret-gated jobs for Azure / GitHub Actions to call on a schedule.
"""
import logging
import secrets

from django.conf import settings
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
    throttle_classes,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .throttles import InternalJobThrottle

logger = logging.getLogger('clients')


def _job_authorized(request):
    expected = (getattr(settings, 'TEAMS_ALERT_JOB_SECRET', '') or '').strip()
    if not expected:
        return bool(getattr(settings, 'DEBUG', False))
    provided = (
        (request.GET.get('token') or '')
        or (request.headers.get('X-Job-Secret') or '')
    ).strip()
    if not provided or len(provided) != len(expected):
        return False
    return secrets.compare_digest(provided, expected)


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([InternalJobThrottle])
def stale_applicant_alerts_job(request):
    """
    Daily trigger: post 3-week applicant outreach alerts to Teams.

    Point the scheduler at /api/jobs/stale-applicant-alerts/?token=<TEAMS_ALERT_JOB_SECRET>.
    """
    if not _job_authorized(request):
        return Response({'error': 'Unauthorized.'}, status=status.HTTP_403_FORBIDDEN)

    from .teams_alerts import send_stale_applicant_alerts

    dry_run = str(request.GET.get('dry_run') or '').lower() in {'1', 'true', 'yes'}
    result = send_stale_applicant_alerts(dry_run=dry_run)
    logger.info(
        'Stale applicant Teams job: due=%s sent=%s skipped=%s errors=%s channel=%s',
        result['due'],
        result['sent'],
        result['skipped'],
        result['errors'],
        result['channel'],
    )
    return Response(
        {
            'ok': result['errors'] == 0,
            'due': result['due'],
            'sent': result['sent'],
            'skipped': result['skipped'],
            'errors': result['errors'],
            'channel': result['channel'],
        }
    )
