"""
Send 30/60/90/120 day client progress follow-up SMS messages.

Run daily from Azure WebJob/Cron:
    python manage.py send_progress_sms_followups
    python manage.py send_progress_sms_followups --dry-run
"""
from datetime import date

from django.core.management.base import BaseCommand

from clients.notifications import send_due_progress_followups


class Command(BaseCommand):
    help = 'Send Azure SMS progress follow-ups at configured client checkpoints'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show due texts without sending them',
        )
        parser.add_argument(
            '--today',
            type=str,
            help='Override today for testing, format YYYY-MM-DD',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        today = date.fromisoformat(options['today']) if options.get('today') else date.today()

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - no SMS messages will be sent'))

        result = send_due_progress_followups(today=today, dry_run=dry_run)
        due = result.get('due', [])

        self.stdout.write(f'Progress SMS check date: {today}')
        self.stdout.write(f'Found {len(due)} due follow-up text(s).')

        if dry_run:
            for client, checkpoint, _dedupe_key in due[:25]:
                self.stdout.write(f'  - {client.full_name} ({client.phone}) at {checkpoint} days')
            if len(due) > 25:
                self.stdout.write(f'  ... and {len(due) - 25} more')
            return

        self.stdout.write(self.style.SUCCESS(f'Sent: {result["sent"]}'))
        if result['failed']:
            self.stdout.write(self.style.ERROR(f'Failed: {result["failed"]}'))
        if result['skipped']:
            self.stdout.write(self.style.WARNING(f'Skipped: {result["skipped"]}'))
