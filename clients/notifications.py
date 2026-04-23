"""
Email notification system for case notes, worker onboarding, and schedule updates
"""
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


def send_open_shift_broadcast_emails(open_shift):
    """
    Broadcast a newly opened shift to active worker accounts via email.
    Uses existing org email infrastructure (no third-party SMS dependency).
    """
    from .models_extensions import WorkerAccount

    if not getattr(settings, 'OPEN_SHIFT_EMAIL_ALERTS_ENABLED', True):
        logger.info('Open shift alerts disabled by settings; skipping shift %s', open_shift.pk)
        return {'sent': 0, 'skipped': 0, 'total': 0}

    accounts = (
        WorkerAccount.objects.filter(is_active=True)
        .select_related('client')
        .order_by('client__first_name', 'client__last_name')
    )

    location = (
        open_shift.work_site.name
        if open_shift.work_site
        else (open_shift.location_label or 'Mission Hiring Hall site')
    )
    date_label = open_shift.shift_date.strftime('%A, %b %d')
    time_label = f"{open_shift.start_time.strftime('%I:%M %p')} - {open_shift.end_time.strftime('%I:%M %p')}"

    sent = 0
    skipped = 0
    total = accounts.count()

    for account in accounts:
        email = (account.client.email or '').strip()
        if not email:
            skipped += 1
            continue

        worker_name = account.client.first_name or account.client.full_name
        subject = f"Open shift available: {open_shift.role_title} on {open_shift.shift_date.strftime('%b %d')}"
        notes_line = f"Notes: {open_shift.notes}\n" if open_shift.notes else ''
        plain = (
            f"Hi {worker_name},\n\n"
            f"A new open shift is available.\n\n"
            f"Role: {open_shift.role_title}\n"
            f"Location: {location}\n"
            f"Date: {date_label}\n"
            f"Time: {time_label}\n"
            f"{notes_line}\n"
            f"Log in to the worker portal to respond:\n"
            f"{WORKER_PORTAL_URL}\n\n"
            f"Mission Hiring Hall\n"
        )

        if _send(subject, plain, None, email):
            sent += 1
        else:
            skipped += 1

    logger.info(
        'Open shift broadcast complete for shift %s: sent=%s skipped=%s total=%s',
        open_shift.pk, sent, skipped, total
    )
    return {'sent': sent, 'skipped': skipped, 'total': total}


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

