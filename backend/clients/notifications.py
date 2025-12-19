"""
Email notification system for case note follow-ups
"""
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import date, timedelta
import logging

logger = logging.getLogger('clients')


def send_followup_alert(case_note, user_email):
    """
    Send email alert for a case note follow-up
    
    Args:
        case_note: CaseNote instance
        user_email: Email address of the user to notify
    """
    try:
        from django.urls import reverse
        
        # Calculate days until/overdue
        days_diff = (case_note.follow_up_date - date.today()).days
        status = "OVERDUE" if days_diff < 0 else f"Due in {days_diff} day{'s' if days_diff != 1 else ''}"
        
        # Build admin URL for the case note
        admin_url = None
        try:
            base_url = getattr(settings, 'ADMIN_BASE_URL', None)
            if not base_url:
                base_url = 'https://mhh-client-backend-cuambzgeg3dfbphd.centralus-01.azurewebsites.net'
            admin_url = f"{base_url}/admin/clients/casenote/{case_note.pk}/change/"
        except Exception as e:
            logger.warning(f"Could not build admin URL: {e}")
            pass
        
        # Prepare email context
        context = {
            'case_note': case_note,
            'client': case_note.client,
            'status': status,
            'days_diff': days_diff,
            'is_overdue': days_diff < 0,
            'admin_url': admin_url,
            'follow_up_date': case_note.follow_up_date,
        }
        
        # Render email templates
        subject = f"⚠️ Follow-up Alert: {case_note.client.full_name} - {status}"
        
        # Try to render HTML email, fallback to plain text
        try:
            html_message = render_to_string('clients/emails/followup_alert.html', context)
            plain_message = render_to_string('clients/emails/followup_alert.txt', context)
        except Exception as e:
            logger.warning(f"Could not render email templates: {e}")
            # Fallback to simple text email
            plain_message = f"""
Case Note Follow-up Alert

Client: {case_note.client.full_name}
Note Type: {case_note.get_note_type_display()}
Follow-up Date: {case_note.follow_up_date}
Status: {status}

Note Content:
{case_note.content[:200]}...

Next Steps:
{case_note.next_steps or 'None specified'}

View in Admin: {admin_url or 'N/A'}
"""
            html_message = None
        
        # Send email
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@missionhiringhall.org')
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=from_email,
            recipient_list=[user_email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Follow-up alert email sent to {user_email} for case note {case_note.pk}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send follow-up alert email: {e}", exc_info=True)
        return False


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
    
    for note in case_notes:
        try:
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
    }

