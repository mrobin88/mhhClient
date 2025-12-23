"""
Management command to send email alerts for case note follow-ups
Run this daily via cron or scheduled task
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from clients.notifications import check_and_send_followup_alerts
import logging

logger = logging.getLogger('clients')


class Command(BaseCommand):
    help = 'Send email alerts for case note follow-ups that are due or overdue'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days-before',
            type=int,
            default=1,
            help='Send alerts this many days before the follow-up date (default: 1)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be sent without actually sending emails',
        )
        parser.add_argument(
            '--overdue-only',
            action='store_true',
            help='Only send alerts for overdue follow-ups (past due date)',
        )

    def handle(self, *args, **options):
        days_before = options['days_before']
        dry_run = options['dry_run']
        overdue_only = options['overdue_only']
        
        self.stdout.write(self.style.SUCCESS('Checking for case note follow-ups...'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No emails will be sent'))
        
        from clients.models import CaseNote
        
        today = date.today()
        if overdue_only:
            # Only overdue
            case_notes = CaseNote.objects.filter(
                follow_up_date__lt=today
            ).exclude(follow_up_date__isnull=True)
            self.stdout.write(f'Checking for OVERDUE follow-ups only (before {today})')
        else:
            # Due today or in the next N days, or overdue
            alert_date = today + timedelta(days=days_before)
            case_notes = CaseNote.objects.filter(
                follow_up_date__lte=alert_date
            ).exclude(follow_up_date__isnull=True)
            self.stdout.write(f'Checking for follow-ups due by {alert_date} (within {days_before} day(s))')
        
        total = case_notes.count()
        self.stdout.write(f'Found {total} case note(s) with follow-ups')
        
        if total == 0:
            self.stdout.write(self.style.SUCCESS('No follow-ups to process'))
            return
        
        if dry_run:
            self.stdout.write('\nWould send alerts for:')
            for note in case_notes[:10]:  # Show first 10
                days_diff = (note.follow_up_date - today).days
                status = "OVERDUE" if days_diff < 0 else f"Due in {days_diff} day(s)"
                self.stdout.write(
                    f'  - {note.client.full_name} ({note.get_note_type_display()}) '
                    f'- {note.follow_up_date} - {status}'
                )
            if total > 10:
                self.stdout.write(f'  ... and {total - 10} more')
        else:
            # Actually send emails
            result = check_and_send_followup_alerts(days_before=days_before)
            
            self.stdout.write(self.style.SUCCESS(
                f'\n✅ Processed {result["total_notes"]} case note(s)'
            ))
            self.stdout.write(self.style.SUCCESS(
                f'📧 Sent {result["emails_sent"]} email alert(s)'
            ))
            
            if result['errors'] > 0:
                self.stdout.write(self.style.ERROR(
                    f'❌ {result["errors"]} error(s) occurred'
                ))
            
            if result['emails_sent'] > 0:
                self.stdout.write(self.style.SUCCESS(
                    '\nFollow-up alerts sent successfully!'
                ))

