"""
Daily notification command - run via Azure WebJob or cron.
Sends: overdue follow-up alerts to staff + tomorrow's schedule reminders to workers.

Usage:
    python manage.py send_daily_notifications
    python manage.py send_daily_notifications --dry-run
"""
from django.core.management.base import BaseCommand
from datetime import date
import logging

logger = logging.getLogger('clients')


class Command(BaseCommand):
    help = 'Send daily email notifications: follow-up alerts + schedule reminders'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be sent without actually sending',
        )
        parser.add_argument(
            '--skip-followups',
            action='store_true',
            help='Skip case note follow-up alerts',
        )
        parser.add_argument(
            '--skip-reminders',
            action='store_true',
            help='Skip schedule reminders',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - no emails will be sent\n'))

        # 1. Case note follow-up alerts
        if not options['skip_followups']:
            self.stdout.write('--- Case Note Follow-up Alerts ---')
            self._send_followup_alerts(dry_run)

        # 2. Tomorrow's schedule reminders
        if not options['skip_reminders']:
            self.stdout.write('\n--- Schedule Reminders (Tomorrow) ---')
            self._send_schedule_reminders(dry_run)

        self.stdout.write(self.style.SUCCESS('\nDone.'))

    def _send_followup_alerts(self, dry_run):
        from clients.notifications import check_and_send_followup_alerts
        from clients.models import CaseNote
        from datetime import timedelta

        tomorrow = date.today() + timedelta(days=1)
        pending = CaseNote.objects.filter(
            follow_up_date__lte=tomorrow,
        ).exclude(follow_up_date__isnull=True).count()

        self.stdout.write(f'Found {pending} case note(s) with follow-ups due by tomorrow')

        if pending == 0:
            self.stdout.write('Nothing to send.')
            return

        if dry_run:
            notes = CaseNote.objects.filter(
                follow_up_date__lte=tomorrow,
            ).exclude(follow_up_date__isnull=True).select_related('client')[:10]
            for note in notes:
                days = (note.follow_up_date - date.today()).days
                status = 'OVERDUE' if days < 0 else f'Due in {days} day(s)'
                self.stdout.write(f'  {note.client.full_name} - {status} - {note.staff_member}')
            return

        result = check_and_send_followup_alerts(days_before=1)
        self.stdout.write(f'Sent {result["emails_sent"]} alert(s), {result["errors"]} error(s)')

    def _send_schedule_reminders(self, dry_run):
        from clients.notifications import send_schedule_reminders
        from clients.models_extensions import WorkAssignment
        from datetime import timedelta

        tomorrow = date.today() + timedelta(days=1)
        assignments = WorkAssignment.objects.filter(
            assignment_date=tomorrow,
            status__in=['pending', 'confirmed'],
        ).select_related('client', 'work_site')

        self.stdout.write(f'Found {assignments.count()} assignment(s) for tomorrow')

        if assignments.count() == 0:
            self.stdout.write('Nothing to send.')
            return

        if dry_run:
            for a in assignments[:10]:
                has_email = 'email' if a.client.email else 'NO EMAIL'
                self.stdout.write(
                    f'  {a.client.full_name} @ {a.work_site.name} '
                    f'{a.start_time.strftime("%I:%M %p")}-{a.end_time.strftime("%I:%M %p")} '
                    f'({has_email})'
                )
            return

        result = send_schedule_reminders()
        self.stdout.write(
            f'Sent {result["sent"]} reminder(s), '
            f'{result["skipped"]} skipped (no email)'
        )
