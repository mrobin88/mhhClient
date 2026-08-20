from django.core.management.base import BaseCommand
from users.models import StaffUser


class Command(BaseCommand):
    help = 'Create an admin user with explicitly supplied recovery credentials'

    def add_arguments(self, parser):
        parser.add_argument('--username', default='admin', help='Admin username')
        parser.add_argument('--email', required=True, help='Admin recovery email')
        parser.add_argument('--password', required=True, help='Strong initial password')

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options['password']

        if StaffUser.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(f'User "{username}" already exists')
            )
            return

        user = StaffUser.objects.create_superuser(
            username=username,
            email=email,
            password=password,
            role='admin'
        )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created admin user: {username}')
        )
        self.stdout.write(f'Username: {username}')
        self.stdout.write('The supplied password was not printed. Store it securely.')
