from django.core.management.base import BaseCommand
from django.utils import timezone

from clients.models import GuardCardEnrollment


class Command(BaseCommand):
    help = 'List Guard Card enrollments whose next follow-up date is today or overdue.'

    def handle(self, *args, **options):
        today = timezone.localdate()
        enrollments = (
            GuardCardEnrollment.objects
            .filter(next_follow_up_date__lte=today)
            .select_related('client')
            .order_by('next_follow_up_date', 'client__last_name', 'client__first_name')
        )

        count = enrollments.count()
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No Guard Card follow-ups are due.'))
            return

        self.stdout.write(self.style.WARNING(f'{count} Guard Card follow-up(s) due:'))
        for enrollment in enrollments:
            client = enrollment.client
            self.stdout.write(
                f'- {client.full_name} | {client.phone or "no phone"} | '
                f'due {enrollment.next_follow_up_date} | barrier: {enrollment.get_barrier_display()}'
            )
