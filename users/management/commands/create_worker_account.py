"""
Management command to create worker portal accounts
"""
from django.core.management.base import BaseCommand
from clients.models import Client
from clients.models_extensions import WorkerAccount


class Command(BaseCommand):
    help = 'Create a worker portal account for a client'

    def add_arguments(self, parser):
        parser.add_argument('phone', type=str, help='Phone number of the client')
        parser.add_argument('--pin', type=str, default=None, help='PIN (default: last 4 digits of phone)')
        parser.add_argument('--approve', action='store_true', help='Auto-approve the account')

    def handle(self, *args, **options):
        phone = options['phone']
        pin = options['pin']
        approve = options['approve']

        try:
            # Find client by phone
            client = Client.objects.get(phone=phone)
        except Client.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'No client found with phone: {phone}'))
            return

        # Check if account already exists
        if hasattr(client, 'worker_account'):
            self.stdout.write(self.style.WARNING(f'Worker account already exists for {client.full_name}'))
            return

        # Set default PIN to last 4 digits of phone if not provided
        if not pin:
            pin = phone[-4:] if len(phone) >= 4 else '1234'

        # Create worker account
        account = WorkerAccount.objects.create(
            client=client,
            phone=phone,
            is_active=True,
            is_approved=approve,
            created_by='CLI Command'
        )
        account.set_pin(pin)
        account.save()

        status = 'approved and active' if approve else 'pending approval'
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Created worker account for {client.full_name} ({status})\n'
                f'   Phone: {phone}\n'
                f'   PIN: {pin}\n'
                f'   Account ID: {account.id}'
            )
        )

        if not approve:
            self.stdout.write(
                self.style.WARNING(
                    '⚠️  Account is pending approval. Approve in Django Admin or run with --approve flag.'
                )
            )
