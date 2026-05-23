"""
Email notification system for case notes, worker onboarding, and schedule updates
"""
import re

from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import date, timedelta
import logging

logger = logging.getLogger('clients')

WORKER_PORTAL_URL = 'https://blue-glacier-0c5f06410.3.azurestaticapps.net/worker.html'


def followup_stage(follow_up_date, today=None):
    """
    Return follow-up aging bucket for dashboards/scorecards.
    """
    if not follow_up_date:
        return 'no_followup'
    today = today or date.today()
    days_overdue = (today - follow_up_date).days
    if days_overdue <= 0:
        return 'current'
    if days_overdue >= 90:
        return 'overdue_90_plus'
    if days_overdue >= 60:
        return 'overdue_60_plus'
    if days_overdue >= 30:
        return 'overdue_30_plus'
    return 'overdue_under_30'


def _get_admin_base_url():
    return getattr(settings, 'ADMIN_BASE_URL', 'https://mhh-client-backend-cuambzgeg3dfbphd.centralus-01.azurewebsites.net')

def _get_from_email():
    return getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@missionhiringhall.org')

def _send(subject, plain, html, recipient):
    """Send an email, return True on success."""
    try:
        send_mail(
            subject=subject,
            message=plain,
            from_email=_get_from_email(),
            recipient_list=[recipient],
            html_message=html,
            fail_silently=False,
        )
        logger.info('Email sent to %s: %s', recipient, subject)
        return True
    except Exception as e:
        logger.error('Email failed to %s: %s', recipient, e, exc_info=True)
        return False


def send_followup_alert(case_note, user_email):
    """Send email alert for a case note follow-up."""
    try:
        days_diff = (case_note.follow_up_date - date.today()).days
        status = "OVERDUE" if days_diff < 0 else f"Due in {days_diff} day{'s' if days_diff != 1 else ''}"
        admin_url = f"{_get_admin_base_url()}/admin/clients/casenote/{case_note.pk}/change/"

        context = {
            'case_note': case_note,
            'client': case_note.client,
            'status': status,
            'days_diff': days_diff,
            'is_overdue': days_diff < 0,
            'admin_url': admin_url,
            'follow_up_date': case_note.follow_up_date,
        }

        subject = f"Follow-up Alert: {case_note.client.full_name} - {status}"
        try:
            html = render_to_string('clients/emails/followup_alert.html', context)
            plain = render_to_string('clients/emails/followup_alert.txt', context)
        except Exception:
            html = None
            plain = (
                f"Case Note Follow-up Alert\n\n"
                f"Client: {case_note.client.full_name}\n"
                f"Follow-up Date: {case_note.follow_up_date}\n"
                f"Status: {status}\n\n"
                f"View in Admin: {admin_url}\n"
            )

        return _send(subject, plain, html, user_email)
    except Exception as e:
        logger.error('Failed to send follow-up alert: %s', e, exc_info=True)
        return False


def send_worker_welcome_email(worker_account):
    """
    Send welcome email when a worker account is approved.
    Returns True if sent, False if skipped or failed.
    """
    client = worker_account.client
    email = client.email
    if not email:
        logger.warning(
            'No email for worker %s (client %s) - skipping welcome email',
            worker_account.phone, client.full_name
        )
        return False

    context = {
        'worker_name': client.first_name or client.full_name,
        'full_name': client.full_name,
        'phone': worker_account.phone,
        'portal_url': WORKER_PORTAL_URL,
    }

    subject = f"Welcome to the Worker Portal - {client.first_name}"
    try:
        html = render_to_string('clients/emails/worker_welcome.html', context)
        plain = render_to_string('clients/emails/worker_welcome.txt', context)
    except Exception:
        html = None
        plain = (
            f"Hi {context['worker_name']},\n\n"
            f"Your worker portal account has been approved.\n\n"
            f"Log in here: {WORKER_PORTAL_URL}\n"
            f"Phone: {context['phone']}\n"
            f"PIN: Last 4 digits of your phone number\n\n"
            f"From there you can see your schedule, confirm shifts, "
            f"and report any issues at your site.\n\n"
            f"Questions? Talk to your supervisor.\n"
        )

    return _send(subject, plain, html, email)


def send_assignment_notification(assignment):
    """
    Send email when a worker gets a new or updated assignment.
    Returns True if sent, False if skipped or failed.
    """
    client = assignment.client
    email = client.email
    if not email:
        logger.warning(
            'No email for client %s - skipping assignment notification',
            client.full_name
        )
        return False

    context = {
        'worker_name': client.first_name or client.full_name,
        'site_name': assignment.work_site.name,
        'site_address': assignment.work_site.address,
        'assignment_date': assignment.assignment_date,
        'start_time': assignment.start_time,
        'end_time': assignment.end_time,
        'supervisor_name': assignment.work_site.supervisor_name,
        'supervisor_phone': assignment.work_site.supervisor_phone,
        'status': assignment.get_status_display(),
        'notes': assignment.assignment_notes,
        'portal_url': WORKER_PORTAL_URL,
    }

    subject = f"Shift Update: {assignment.work_site.name} on {assignment.assignment_date.strftime('%b %d')}"
    try:
        html = render_to_string('clients/emails/assignment_notification.html', context)
        plain = render_to_string('clients/emails/assignment_notification.txt', context)
    except Exception:
        html = None
        plain = (
            f"Hi {context['worker_name']},\n\n"
            f"You have a shift update:\n\n"
            f"Site: {context['site_name']}\n"
            f"Address: {context['site_address']}\n"
            f"Date: {context['assignment_date']}\n"
            f"Time: {context['start_time'].strftime('%I:%M %p')} - {context['end_time'].strftime('%I:%M %p')}\n"
            f"Supervisor: {context['supervisor_name']} {context['supervisor_phone']}\n\n"
            f"Confirm your shift: {WORKER_PORTAL_URL}\n"
        )

    return _send(subject, plain, html, email)


def send_schedule_reminders():
    """
    Send reminder emails to workers with assignments tomorrow.
    Returns dict with counts.
    """
    from .models_extensions import WorkAssignment

    tomorrow = date.today() + timedelta(days=1)
    assignments = WorkAssignment.objects.filter(
        assignment_date=tomorrow,
        status__in=['pending', 'confirmed'],
    ).select_related('client', 'work_site')

    sent = 0
    skipped = 0

    for assignment in assignments:
        email = assignment.client.email
        if not email:
            skipped += 1
            continue

        context = {
            'worker_name': assignment.client.first_name or assignment.client.full_name,
            'site_name': assignment.work_site.name,
            'site_address': assignment.work_site.address,
            'assignment_date': assignment.assignment_date,
            'start_time': assignment.start_time,
            'end_time': assignment.end_time,
            'supervisor_name': assignment.work_site.supervisor_name,
            'supervisor_phone': assignment.work_site.supervisor_phone,
            'portal_url': WORKER_PORTAL_URL,
        }

        subject = f"Reminder: You work at {assignment.work_site.name} tomorrow"
        try:
            html = render_to_string('clients/emails/schedule_reminder.html', context)
            plain = render_to_string('clients/emails/schedule_reminder.txt', context)
        except Exception:
            html = None
            plain = (
                f"Hi {context['worker_name']},\n\n"
                f"Reminder: You have a shift tomorrow.\n\n"
                f"Site: {context['site_name']}\n"
                f"Address: {context['site_address']}\n"
                f"Time: {context['start_time'].strftime('%I:%M %p')} - "
                f"{context['end_time'].strftime('%I:%M %p')}\n"
                f"Supervisor: {context['supervisor_name']} {context['supervisor_phone']}\n\n"
                f"View your schedule: {WORKER_PORTAL_URL}\n"
            )

        if _send(subject, plain, html, email):
            sent += 1

    logger.info('Schedule reminders: %d sent, %d skipped (no email)', sent, skipped)
    return {'sent': sent, 'skipped': skipped, 'total': assignments.count()}


def send_pitstop_application_alert(application):
    """
    Send alert email when a new Pit Stop application is submitted.
    Uses PITSTOP_APPLICATION_ALERT_EMAILS env (comma-separated).
    """
    recipients = getattr(settings, 'PITSTOP_APPLICATION_ALERT_EMAILS', '')
    if isinstance(recipients, str):
        recipients = [r.strip() for r in recipients.split(',') if r.strip()]
    if not recipients:
        logger.info('No PITSTOP_APPLICATION_ALERT_EMAILS configured; skipping alert for application %s', application.pk)
        return {'sent': 0, 'total': 0}

    client = application.client
    day_count = len(application.available_days_list)
    subject = f"New Pit Stop Application: {client.full_name}"
    plain = (
        f"New Pit Stop application submitted.\n\n"
        f"Client: {client.full_name}\n"
        f"Phone: {client.phone or '-'}\n"
        f"Email: {client.email or '-'}\n"
        f"Position: {application.position_applied_for}\n"
        f"Start Date: {application.available_start_date or '-'}\n"
        f"Employment Desired: {', '.join(application.employment_desired or []) or '-'}\n"
        f"Days Available: {day_count}\n"
        f"Submitted At: {application.created_at}\n\n"
        f"Review in admin:\n"
        f"{_get_admin_base_url()}/admin/clients/pitstopapplication/{application.pk}/change/\n"
    )

    sent = 0
    for recipient in recipients:
        if _send(subject, plain, None, recipient):
            sent += 1
    return {'sent': sent, 'total': len(recipients)}


def _sms_client():
    connection_string = getattr(settings, 'AZURE_COMMUNICATION_CONNECTION_STRING', '')
    if not connection_string:
        raise RuntimeError('AZURE_COMMUNICATION_CONNECTION_STRING is not configured')
    try:
        from azure.communication.sms import SmsClient
    except ImportError as exc:
        raise RuntimeError('azure-communication-sms is not installed') from exc
    return SmsClient.from_connection_string(connection_string)


def _sms_from_number():
    from_number = getattr(settings, 'AZURE_COMMUNICATION_SMS_FROM', '')
    if not from_number:
        raise RuntimeError('AZURE_COMMUNICATION_SMS_FROM is not configured')
    return from_number


def _to_e164_us(phone):
    from .phone_utils import normalize_login_phone, phone_digits

    raw = str(phone or '').strip()
    raw = re.sub(r'(?i)\s*(?:ext\.?|x|#)\s*\d+\s*$', '', raw)
    digits = normalize_login_phone(raw)
    if len(digits) == 10:
        return f'+1{digits}'
    if len(digits) == 11 and digits.startswith('1'):
        return f'+{digits}'
    # Keep international-style +numbers if they are already entered that way.
    if raw.startswith('+'):
        raw_digits = phone_digits(raw)
        if len(raw_digits) >= 10:
            return f'+{raw_digits}'
    return ''


def _normalize_us_digits(phone):
    """Normalize to 11-digit US format (1XXXXXXXXXX) when possible."""
    from .phone_utils import normalize_login_phone

    digits = normalize_login_phone(phone or '')
    if len(digits) == 10:
        return f'1{digits}'
    if len(digits) == 11 and digits.startswith('1'):
        return digits
    return ''


def _compliance_footer():
    if not getattr(settings, 'SMS_APPEND_COMPLIANCE_FOOTER', True):
        return ''
    return getattr(settings, 'SMS_COMPLIANCE_FOOTER', ' Reply STOP to opt out.')


def _compose_sms_body(body):
    # Keep messages under segment-heavy lengths while preserving compliance footer.
    content = (body or '').strip()
    footer = _compliance_footer()
    if not footer:
        return content[:480]
    reserve = max(480 - len(footer), 0)
    return f'{content[:reserve].rstrip()}{footer}'


def _is_internal_phone_allowed(to_phone):
    """
    When internal-only mode is enabled, allow sends only to known app records.
    """
    if not getattr(settings, 'SMS_INTERNAL_ONLY', False):
        return True

    target_digits = _normalize_us_digits(to_phone)
    if not target_digits:
        return False

    from .models import Client
    from .models_extensions import WorkerAccount
    from users.models import StaffUser

    for raw_phone in Client.objects.exclude(phone__isnull=True).exclude(phone='').values_list('phone', flat=True):
        if _normalize_us_digits(raw_phone) == target_digits:
            return True
    for raw_phone in WorkerAccount.objects.exclude(phone='').values_list('phone', flat=True):
        if _normalize_us_digits(raw_phone) == target_digits:
            return True
    for raw_phone in StaffUser.objects.exclude(phone__isnull=True).exclude(phone='').values_list('phone', flat=True):
        if _normalize_us_digits(raw_phone) == target_digits:
            return True
    return False


def send_phone_text_message(phone, body, require_enabled_flag=False):
    """
    Send SMS to a raw phone number (not tied to a Client row).
    Returns (success: bool, detail: str).
    """
    to_phone = _to_e164_us(phone)
    if not to_phone:
        return False, 'Phone is not a valid SMS number'
    if not _is_internal_phone_allowed(to_phone):
        return False, 'Phone is not allowlisted for internal-only SMS mode'
    if require_enabled_flag and not getattr(settings, 'SMS_FOLLOWUP_ENABLED', False):
        return False, 'SMS_FOLLOWUP_ENABLED is false'

    try:
        result = _sms_client().send(
            from_=_sms_from_number(),
            to=[to_phone],
            message=_compose_sms_body(body),
            enable_delivery_report=True,
        )[0]
        if getattr(result, 'successful', False):
            message_id = getattr(result, 'message_id', '') or ''
            return True, f'{to_phone} ({message_id})' if message_id else to_phone
        err = getattr(result, 'error_message', '') or 'Azure SMS send failed'
        return False, err
    except Exception as exc:
        return False, str(exc)


def send_text_message(
    client,
    body,
    purpose='general',
    checkpoint_days=None,
    dedupe_key=None,
    require_enabled_flag=True,
):
    """
    Send and log one SMS via Azure Communication Services.
    If dedupe_key already exists as sent/pending, return that row instead of sending again.
    """
    from django.utils import timezone
    from .models_extensions import ClientTextMessage

    if dedupe_key:
        existing = ClientTextMessage.objects.filter(dedupe_key=dedupe_key).first()
        if existing and existing.status in {
            ClientTextMessage.STATUS_PENDING,
            ClientTextMessage.STATUS_SENT,
        }:
            return existing, False

    to_phone = _to_e164_us(client.phone)
    from_phone = getattr(settings, 'AZURE_COMMUNICATION_SMS_FROM', '')
    log_defaults = {
        'client': client,
        'direction': ClientTextMessage.DIRECTION_OUTBOUND,
        'purpose': purpose,
        'checkpoint_days': checkpoint_days,
        'to_phone': to_phone,
        'from_phone': from_phone,
        'body': body,
        'status': ClientTextMessage.STATUS_PENDING,
    }
    if dedupe_key:
        log, _ = ClientTextMessage.objects.get_or_create(
            dedupe_key=dedupe_key,
            defaults=log_defaults,
        )
    else:
        log = ClientTextMessage.objects.create(**log_defaults)

    if log.status == ClientTextMessage.STATUS_FAILED:
        log.to_phone = to_phone
        log.from_phone = from_phone
        log.body = body
        log.status = ClientTextMessage.STATUS_PENDING
        log.error_message = ''
        log.save(
            update_fields=[
                'to_phone',
                'from_phone',
                'body',
                'status',
                'error_message',
                'updated_at',
            ]
        )

    if not to_phone:
        log.status = ClientTextMessage.STATUS_FAILED
        log.error_message = 'Client phone is not a valid SMS number'
        log.save(update_fields=['status', 'error_message', 'updated_at'])
        return log, True

    if require_enabled_flag and not getattr(settings, 'SMS_FOLLOWUP_ENABLED', False):
        log.status = ClientTextMessage.STATUS_FAILED
        log.error_message = 'SMS_FOLLOWUP_ENABLED is false'
        log.save(update_fields=['status', 'error_message', 'updated_at'])
        return log, True

    try:
        result = _sms_client().send(
            from_=_sms_from_number(),
            to=[to_phone],
            message=_compose_sms_body(body),
            enable_delivery_report=True,
        )[0]
        log.provider_message_id = getattr(result, 'message_id', '') or ''
        log.provider_response = {
            'successful': getattr(result, 'successful', None),
            'http_status_code': getattr(result, 'http_status_code', None),
            'error_message': getattr(result, 'error_message', None),
        }
        if getattr(result, 'successful', False):
            log.status = ClientTextMessage.STATUS_SENT
            log.sent_at = timezone.now()
            log.error_message = ''
        else:
            log.status = ClientTextMessage.STATUS_FAILED
            log.error_message = getattr(result, 'error_message', '') or 'Azure SMS send failed'
    except Exception as exc:
        log.status = ClientTextMessage.STATUS_FAILED
        log.error_message = str(exc)

    log.save(
        update_fields=[
            'status',
            'provider_message_id',
            'provider_response',
            'error_message',
            'sent_at',
            'updated_at',
        ]
    )
    return log, True


def progress_followup_body(client, checkpoint_days):
    first_name = (client.first_name or client.full_name or 'there').strip()
    return (
        f'Hi {first_name}, this is Mission Hiring Hall checking in {checkpoint_days} days after your intake. '
        'Please reply or call us to share your progress, make an appointment, or continue your work with us. '
        'Mission Hiring Hall'
    )


def _progress_anchor_date(client):
    start_field = getattr(settings, 'SMS_FOLLOWUP_START_FIELD', 'created_at')
    anchor = getattr(client, start_field, None) or client.created_at
    if hasattr(anchor, 'date'):
        return anchor.date()
    return anchor


def send_due_progress_followups(today=None, dry_run=False):
    """
    Send progress follow-up SMS at configured checkpoint days after client intake/start.
    Intended to run daily from Azure WebJob/Cron.
    """
    from datetime import date, timedelta
    from .models import Client
    from .models_extensions import ClientTextMessage

    today = today or date.today()
    checkpoints = getattr(settings, 'SMS_FOLLOWUP_CHECKPOINT_DAYS', [30, 60, 90, 120])
    window_days = max(int(getattr(settings, 'SMS_FOLLOWUP_WINDOW_DAYS', 1)), 1)
    start_field = getattr(settings, 'SMS_FOLLOWUP_START_FIELD', 'created_at')
    needed_fields = {'id', 'first_name', 'last_name', 'phone', 'created_at'}
    if start_field != 'created_at':
        needed_fields.add(start_field)
    clients = Client.objects.exclude(phone__isnull=True).exclude(phone='').only(*needed_fields)

    due = []
    for client in clients.iterator(chunk_size=500):
        anchor = _progress_anchor_date(client)
        if not anchor:
            continue
        age_days = (today - anchor).days
        for checkpoint in checkpoints:
            if checkpoint <= age_days < checkpoint + window_days:
                dedupe_key = f'client:{client.pk}:progress-followup:{checkpoint}'
                if ClientTextMessage.objects.filter(
                    dedupe_key=dedupe_key,
                    status__in=[
                        ClientTextMessage.STATUS_PENDING,
                        ClientTextMessage.STATUS_SENT,
                    ],
                ).exists():
                    continue
                due.append((client, checkpoint, dedupe_key))

    if dry_run:
        return {'due': due, 'sent': 0, 'failed': 0, 'skipped': 0, 'total_due': len(due)}

    if not getattr(settings, 'SMS_FOLLOWUP_ENABLED', False):
        return {'due': due, 'sent': 0, 'failed': 0, 'skipped': len(due), 'total_due': len(due)}

    sent = 0
    failed = 0
    skipped = 0
    for client, checkpoint, dedupe_key in due:
        log, attempted = send_text_message(
            client=client,
            body=progress_followup_body(client, checkpoint),
            purpose=ClientTextMessage.PURPOSE_PROGRESS_FOLLOWUP,
            checkpoint_days=checkpoint,
            dedupe_key=dedupe_key,
        )
        if not attempted:
            skipped += 1
        elif log.status == ClientTextMessage.STATUS_SENT:
            sent += 1
        else:
            failed += 1

    return {
        'due': due,
        'sent': sent,
        'failed': failed,
        'skipped': skipped,
        'total_due': len(due),
    }


def check_and_send_followup_alerts(days_before=1, send_to_staff=True):
    """
    Check for case notes with upcoming or overdue follow-ups and send alerts
    
    Args:
        days_before: Send alerts this many days before the follow-up date (default: 1)
        send_to_staff: If True, send to the staff_member email (default: True)
    
    Returns:
        dict with counts of emails sent
    """
    from .models import CaseNote
    from users.models import StaffUser
    
    today = date.today()
    alert_date = today + timedelta(days=days_before)
    
    # Find case notes with follow-ups due or overdue
    case_notes = CaseNote.objects.filter(
        follow_up_date__lte=alert_date
    ).exclude(
        follow_up_date__isnull=True
    ).select_related('client')
    
    sent_count = 0
    error_count = 0
    bucket_counts = {
        'current': 0,
        'overdue_under_30': 0,
        'overdue_30_plus': 0,
        'overdue_60_plus': 0,
        'overdue_90_plus': 0,
    }
    
    for note in case_notes:
        try:
            stage = followup_stage(note.follow_up_date, today=today)
            if stage in bucket_counts:
                bucket_counts[stage] += 1

            # Try to find user by staff_member name or email
            user_email = None
            
            if send_to_staff:
                # Try to match staff_member name to a user
                try:
                    # Try exact match first
                    user = StaffUser.objects.filter(
                        username__iexact=note.staff_member
                    ).first()
                    
                    if not user:
                        # Try matching by first/last name
                        name_parts = note.staff_member.split()
                        if len(name_parts) >= 2:
                            user = StaffUser.objects.filter(
                                first_name__iexact=name_parts[0],
                                last_name__iexact=name_parts[-1]
                            ).first()
                    
                    if user and user.email:
                        user_email = user.email
                except Exception as e:
                    logger.warning(f"Could not find user for staff_member '{note.staff_member}': {e}")
            
            # If no user email found, try to get from settings
            if not user_email:
                # Fallback: send to admin email or configured alert email
                user_email = getattr(settings, 'CASE_NOTE_ALERT_EMAIL', None)
                if not user_email:
                    # Try to get from first superuser
                    try:
                        admin_user = StaffUser.objects.filter(is_superuser=True).first()
                        if admin_user and admin_user.email:
                            user_email = admin_user.email
                    except:
                        pass
            
            if user_email:
                if send_followup_alert(note, user_email):
                    sent_count += 1
                else:
                    error_count += 1
            else:
                logger.warning(f"No email address found for case note {note.pk} follow-up alert")
                error_count += 1
                
        except Exception as e:
            logger.error(f"Error processing follow-up alert for case note {note.pk}: {e}", exc_info=True)
            error_count += 1
    
    return {
        'total_notes': case_notes.count(),
        'emails_sent': sent_count,
        'errors': error_count,
        'bucket_counts': bucket_counts,
    }

