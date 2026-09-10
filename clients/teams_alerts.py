"""
Teams alerts when an applicant has had no staff outreach for 3 weeks.

Posts as PitStopBot (pitstopbot@missionhiringhall.org) into the MHH ALL STAFF
Teams channel via Microsoft Graph sendMail. Optional webhook or channel Graph
post can be configured later.
"""
import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from datetime import timedelta
from html import escape

from django.conf import settings
from django.db.models import Exists, OuterRef
from django.utils import timezone

logger = logging.getLogger('clients')

STALE_DAYS_DEFAULT = 21
GRAPH_SCOPE = 'https://graph.microsoft.com/.default'
GRAPH_TOKEN_URL = 'https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token'
GRAPH_MESSAGE_URL = (
    'https://graph.microsoft.com/v1.0/teams/{team_id}/channels/{channel_id}/messages'
)


def stale_applicant_days():
    return max(int(getattr(settings, 'TEAMS_STALE_APPLICANT_DAYS', STALE_DAYS_DEFAULT)), 1)


def alerts_enabled():
    if not getattr(settings, 'TEAMS_STALE_ALERTS_ENABLED', False):
        return False
    return bool(
        (getattr(settings, 'TEAMS_WEBHOOK_URL', '') or '').strip()
        or _graph_configured()
        or _graph_mail_configured()
        or (getattr(settings, 'TEAMS_ALERT_EMAIL', '') or '').strip()
    )


def _graph_mail_configured():
    return all(
        (getattr(settings, name, '') or '').strip()
        for name in (
            'TEAMS_GRAPH_TENANT_ID',
            'TEAMS_GRAPH_CLIENT_ID',
            'TEAMS_GRAPH_CLIENT_SECRET',
            'TEAMS_BOT_UPN',
            'TEAMS_ALERT_EMAIL',
        )
    )


def _graph_configured():
    return all(
        (getattr(settings, name, '') or '').strip()
        for name in (
            'TEAMS_GRAPH_TENANT_ID',
            'TEAMS_GRAPH_CLIENT_ID',
            'TEAMS_GRAPH_CLIENT_SECRET',
            'TEAMS_GRAPH_TEAM_ID',
            'TEAMS_GRAPH_CHANNEL_ID',
        )
    )


def applied_for_label(client):
    program = client.get_training_interest_display()
    application = client.pitstop_applications.order_by('-created_at').first()
    position = (getattr(application, 'position_applied_for', '') or '').strip()
    if position and client.training_interest == 'pit_stop':
        return f'{program} — {position}'
    if position and 'pit' in program.lower():
        return f'{program} — {position}'
    return program


def staff_client_url(client):
    base = (getattr(settings, 'STAFF_APP_BASE_URL', '') or '').rstrip('/')
    return f'{base}/#/clients/{client.pk}'


def stale_applicants_queryset(today=None):
    from .models import CaseNote, Client, DocumentUploadInvite, PitStopApplication
    from .models_classes import ClassEnrollment
    from .models_extensions import ApplicantStaleAlert, ClientTextMessage

    today = today or timezone.localdate()
    cutoff_date = today - timedelta(days=stale_applicant_days())

    untouched_citybuild = Client.CITYBUILD_STAGE_GENERAL_INTEREST
    untouched_pitstop = Client.PIT_STOP_STAGE_APPLICANT

    has_note = CaseNote.objects.filter(client_id=OuterRef('pk'))
    has_sent_sms = ClientTextMessage.objects.filter(
        client_id=OuterRef('pk'),
        direction=ClientTextMessage.DIRECTION_OUTBOUND,
        status=ClientTextMessage.STATUS_SENT,
    )
    has_class = ClassEnrollment.objects.filter(client_id=OuterRef('pk'))
    has_invite = DocumentUploadInvite.objects.filter(client_id=OuterRef('pk'))
    has_reviewed_pitstop = PitStopApplication.objects.filter(client_id=OuterRef('pk')).exclude(
        review_status=PitStopApplication.REVIEW_NEW,
    )
    already_alerted = ApplicantStaleAlert.objects.filter(client_id=OuterRef('pk'))

    return (
        Client.objects.filter(
            status__in=['active', 'pending'],
            pit_stop_stage=untouched_pitstop,
            citybuild_stage=untouched_citybuild,
            created_at__date__lte=cutoff_date,
        )
        .filter(worker_account__isnull=True)
        .annotate(
            has_note=Exists(has_note),
            has_sent_sms=Exists(has_sent_sms),
            has_class=Exists(has_class),
            has_invite=Exists(has_invite),
            has_reviewed_pitstop=Exists(has_reviewed_pitstop),
            already_alerted=Exists(already_alerted),
        )
        .filter(
            has_note=False,
            has_sent_sms=False,
            has_class=False,
            has_invite=False,
            has_reviewed_pitstop=False,
            already_alerted=False,
        )
        .order_by('created_at')
    )


def _days_since_applied(client, today=None):
    today = today or timezone.localdate()
    applied = timezone.localtime(client.created_at).date() if timezone.is_aware(client.created_at) else client.created_at.date()
    return max((today - applied).days, 0)


def _rows_for(clients, today=None):
    today = today or timezone.localdate()
    rows = []
    for client in clients:
        rows.append(
            {
                'client': client,
                'name': client.full_name,
                'applied_for': applied_for_label(client),
                'phone': (client.phone or '').strip(),
                'days_stale': _days_since_applied(client, today=today),
                'url': staff_client_url(client),
            }
        )
    return rows


def _plain_body(rows):
    lines = [
        f'{len(rows)} applicant{"s" if len(rows) != 1 else ""} applied at least {stale_applicant_days()} weeks ago and nobody has reached out yet.',
        '',
    ]
    for row in rows:
        lines.append(f"- {row['name']}")
        lines.append(f"  Applied for: {row['applied_for']}")
        if row['phone']:
            lines.append(f"  Phone: {row['phone']}")
        lines.append(f"  Waiting: {row['days_stale']} days")
        lines.append(f"  Open: {row['url']}")
        lines.append('')
    lines.append('A case note, a text, a class signup, a document-upload link, or moving their stage counts as reaching out.')
    return '\n'.join(lines).strip()


def _html_body(rows):
    items = []
    for row in rows:
        phone = f'<div>Phone: {escape(row["phone"])}</div>' if row['phone'] else ''
        items.append(
            '<li style="margin:0 0 12px 0;">'
            f'<div><strong>{escape(row["name"])}</strong></div>'
            f'<div>Applied for: {escape(row["applied_for"])}</div>'
            f'{phone}'
            f'<div>Waiting: {row["days_stale"]} days</div>'
            f'<div><a href="{escape(row["url"], quote=True)}">Open their page</a></div>'
            '</li>'
        )
    count = len(rows)
    noun = 'applicant' if count == 1 else 'applicants'
    return (
        f'<p><strong>{count} {noun}</strong> applied at least {stale_applicant_days()} days ago '
        'and nobody has reached out yet.</p>'
        f'<ul style="padding-left:18px;">{"".join(items)}</ul>'
        '<p>A case note, a text, a class signup, a document-upload link, or moving their stage '
        'counts as reaching out.</p>'
    )


def _adaptive_card(rows):
    facts_blocks = []
    for row in rows[:15]:
        facts_blocks.append(
            {
                'type': 'FactSet',
                'facts': [
                    {'title': 'Name', 'value': row['name']},
                    {'title': 'Applied for', 'value': row['applied_for']},
                    {'title': 'Waiting', 'value': f'{row["days_stale"]} days'},
                    {'title': 'Phone', 'value': row['phone'] or '—'},
                ],
            }
        )
        facts_blocks.append(
            {
                'type': 'ActionSet',
                'actions': [
                    {
                        'type': 'Action.OpenUrl',
                        'title': 'Open their page',
                        'url': row['url'],
                    }
                ],
            }
        )
    extra = len(rows) - 15
    if extra > 0:
        facts_blocks.append(
            {'type': 'TextBlock', 'text': f'…and {extra} more in this digest.', 'wrap': True}
        )
    count = len(rows)
    noun = 'applicant' if count == 1 else 'applicants'
    return {
        '$schema': 'http://adaptivecards.io/schemas/adaptive-card.json',
        'type': 'AdaptiveCard',
        'version': '1.4',
        'body': [
            {
                'type': 'TextBlock',
                'size': 'Medium',
                'weight': 'Bolder',
                'text': f'{count} {noun} waiting 3 weeks with no outreach',
            },
            {
                'type': 'TextBlock',
                'wrap': True,
                'text': 'Nobody has logged a case note, text, class signup, or stage change yet.',
            },
            *facts_blocks,
        ],
    }


def _post_json(url, payload, headers=None, timeout=20, form=False):
    if form:
        data = urllib.parse.urlencode(payload).encode('utf-8')
        content_type = 'application/x-www-form-urlencoded'
    else:
        data = json.dumps(payload).encode('utf-8')
        content_type = 'application/json'
    request = urllib.request.Request(url, data=data, method='POST')
    request.add_header('Content-Type', content_type)
    for key, value in (headers or {}).items():
        request.add_header(key, value)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
            return response.status, body
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode('utf-8', errors='replace')[:800]
        raise RuntimeError(f'HTTP {exc.code} posting to Teams: {detail}') from exc


def _send_webhook(rows):
    from .models_extensions import ApplicantStaleAlert

    url = (getattr(settings, 'TEAMS_WEBHOOK_URL', '') or '').strip()
    if not url:
        return False
    payload = {
        'text': _plain_body(rows),
        'type': 'message',
        'attachments': [
            {
                'contentType': 'application/vnd.microsoft.card.adaptive',
                'content': _adaptive_card(rows),
            }
        ],
    }
    _post_json(url, payload)
    return ApplicantStaleAlert.CHANNEL_WEBHOOK


def _graph_token():
    tenant = settings.TEAMS_GRAPH_TENANT_ID.strip()
    _status, body = _post_json(
        GRAPH_TOKEN_URL.format(tenant=tenant),
        {
            'client_id': settings.TEAMS_GRAPH_CLIENT_ID.strip(),
            'client_secret': settings.TEAMS_GRAPH_CLIENT_SECRET.strip(),
            'scope': GRAPH_SCOPE,
            'grant_type': 'client_credentials',
        },
        form=True,
    )
    data = json.loads(body.decode('utf-8'))
    token = data.get('access_token')
    if not token:
        raise RuntimeError(f'Graph token missing: {data}')
    return token


def _send_graph(rows):
    from .models_extensions import ApplicantStaleAlert

    if not _graph_configured():
        return False
    token = _graph_token()
    html = _html_body(rows)
    url = GRAPH_MESSAGE_URL.format(
        team_id=settings.TEAMS_GRAPH_TEAM_ID.strip(),
        channel_id=urllib.parse.quote(settings.TEAMS_GRAPH_CHANNEL_ID.strip(), safe=':@'),
    )
    _post_json(
        url,
        {'body': {'contentType': 'html', 'content': html}},
        headers={'Authorization': f'Bearer {token}'},
    )
    return ApplicantStaleAlert.CHANNEL_GRAPH


def _send_graph_mail(rows, subject=None, html=None, plain=None):
    """Post to the Teams channel as PitStopBot via Graph sendMail."""
    from .models_extensions import ApplicantStaleAlert

    if not _graph_mail_configured():
        return False
    token = _graph_token()
    bot_upn = settings.TEAMS_BOT_UPN.strip()
    recipient = settings.TEAMS_ALERT_EMAIL.strip()
    count = len(rows)
    noun = 'applicant' if count == 1 else 'applicants'
    payload = {
        'message': {
            'subject': subject or f'3 weeks with no outreach: {count} {noun}',
            'body': {
                'contentType': 'HTML',
                'content': html or _html_body(rows),
            },
            'toRecipients': [{'emailAddress': {'address': recipient}}],
        },
        'saveToSentItems': False,
    }
    _post_json(
        f'https://graph.microsoft.com/v1.0/users/{urllib.parse.quote(bot_upn)}/sendMail',
        payload,
        headers={'Authorization': f'Bearer {token}'},
    )
    return ApplicantStaleAlert.CHANNEL_GRAPH


def send_pitstopbot_hello():
    """One-time introduction posted as PitStopBot to the staff Teams channel."""
    html = (
        "<p>Hello — I'm <b>PitStopBot</b>.</p>"
        "<p>I'll watch the client services app from Azure. If someone applied and nobody "
        "on staff has reached out for <b>3 weeks</b>, I'll post here with their name, "
        "what they applied for, their phone, and a link to their page.</p>"
        "<p>A case note, a text, a class signup, a document-upload link, or moving their "
        "Pit Stop / City Build stage counts as reaching out. Then I won't ping you about them again.</p>"
        "<p>— PitStopBot</p>"
    )
    return _send_graph_mail(
        rows=[],
        subject='Hello from PitStopBot',
        html=html,
        plain="Hello — I'm PitStopBot.",
    )


def _send_email(rows):
    from django.core.mail import send_mail
    from .models_extensions import ApplicantStaleAlert

    recipient = (getattr(settings, 'TEAMS_ALERT_EMAIL', '') or '').strip()
    if not recipient:
        return False
    count = len(rows)
    noun = 'applicant' if count == 1 else 'applicants'
    subject = f'3 weeks with no outreach: {count} {noun}'
    send_mail(
        subject=subject,
        message=_plain_body(rows),
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@missionhiringhall.org'),
        recipient_list=[recipient],
        html_message=_html_body(rows),
        fail_silently=False,
    )
    return ApplicantStaleAlert.CHANNEL_EMAIL


def _deliver(rows):
    errors = []
    for sender in (_send_webhook, _send_graph_mail, _send_graph, _send_email):
        try:
            channel = sender(rows)
        except Exception as exc:
            logger.warning('Teams applicant alert %s failed: %s', sender.__name__, exc, exc_info=True)
            errors.append(str(exc))
            continue
        if channel:
            return channel, errors
    raise RuntimeError('No Teams destination accepted the applicant alert. ' + '; '.join(errors))


def send_stale_applicant_alerts(today=None, dry_run=False):
    """
    Find applicants with no staff outreach for 3 weeks and notify Teams once each.
    """
    from .models_extensions import ApplicantStaleAlert

    today = today or timezone.localdate()
    clients = list(stale_applicants_queryset(today=today).prefetch_related('pitstop_applications'))
    rows = _rows_for(clients, today=today)

    result = {
        'due': len(rows),
        'sent': 0,
        'skipped': 0,
        'errors': 0,
        'channel': '',
        'names': [row['name'] for row in rows],
    }

    if not rows:
        return result
    if dry_run:
        result['skipped'] = len(rows)
        return result
    if not alerts_enabled():
        logger.info('Teams stale-applicant alerts are off or unconfigured; skipping %s people', len(rows))
        result['skipped'] = len(rows)
        return result

    try:
        channel, _errors = _deliver(rows)
    except Exception:
        logger.exception('Failed to post stale-applicant Teams alert')
        result['errors'] = 1
        return result

    for row in rows:
        ApplicantStaleAlert.objects.get_or_create(
            client=row['client'],
            defaults={
                'applied_for': row['applied_for'][:200],
                'days_stale': row['days_stale'],
                'channel': channel,
            },
        )
    result['sent'] = len(rows)
    result['channel'] = channel
    return result
