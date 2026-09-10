"""
Notify Teams when applicants have had no outreach for 3 weeks.

    python manage.py send_stale_applicant_alerts
    python manage.py send_stale_applicant_alerts --dry-run
"""
from datetime import date

from django.core.management.base import BaseCommand

from clients.teams_alerts import send_stale_applicant_alerts, stale_applicant_days


class Command(BaseCommand):
    help = 'Post a Teams alert for applicants with no staff outreach for 3 weeks'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show who would be posted without sending to Teams',
        )
        parser.add_argument(
            '--today',
            type=str,
            help='Override today for testing, format YYYY-MM-DD',
        )

        parser.add_argument(
            '--hello',
            action='store_true',
            help='Post a one-time PitStopBot introduction to Teams',
        )

    def handle(self, *args, **options):
        if options.get('hello'):
            from clients.teams_alerts import send_pitstopbot_hello

            channel = send_pitstopbot_hello()
            if channel:
                self.stdout.write(self.style.SUCCESS(f'PitStopBot hello posted via {channel}.'))
            else:
                self.stdout.write(self.style.ERROR('PitStopBot hello was not sent (not configured).'))
            return
        dry_run = options['dry_run']
        today = date.fromisoformat(options['today']) if options.get('today') else None

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - nothing will be posted to Teams'))

        result = send_stale_applicant_alerts(today=today, dry_run=dry_run)
        days = stale_applicant_days()
        self.stdout.write(f'Looking for applicants with no outreach for {days} days.')
        self.stdout.write(f'Found {result["due"]} applicant(s).')

        for name in result['names'][:25]:
            self.stdout.write(f'  - {name}')
        if result['due'] > 25:
            self.stdout.write(f'  ... and {result["due"] - 25} more')

        if dry_run:
            return

        if result['sent']:
            self.stdout.write(self.style.SUCCESS(
                f'Posted {result["sent"]} applicant(s) to Teams ({result["channel"]}).'
            ))
        elif result['skipped']:
            self.stdout.write('Nothing posted (alerts off, or dry destination).')
        if result['errors']:
            self.stdout.write(self.style.ERROR('Teams post failed. Check logs.'))
