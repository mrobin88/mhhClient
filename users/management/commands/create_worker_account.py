"""
Management command to create worker portal accounts
"""
from django.core.management.base import BaseCommand
from clients.models import Client
from clients.models_extensions import WorkerAccount
from clients.phone_utils import default_worker_pin_from_phone, find_by_normalized_phone


class Command(BaseCommand):
    help = 'Create a worker portal account for a client'

    def add_arguments(self, parser):
        parser.add_argument('phone', type=str, help='Phone number of the client')
        parser.add_argument('--pin', type=str, default=None, help='PIN (default: last 4 digits of phone)')
        parser.add_argument(
            '--inactive',
            action='store_true',
            help='Create the account with portal login off (enable later in admin)',
        )
        parser.add_argument(
            '--approve',
            action='store_true',
            help='No longer required — portal access is on by default. Kept for old scripts.',
        )

    def handle(self, *args, **options):
        phone = options['phone']
        pin = options['pin']
        portal_on = not options['inactive']

        client = find_by_normalized_phone(Client.objects.all(), phone)
        if not client:
            self.stdout.write(self.style.ERROR(f'No client found with phone: {phone}'))
            return

        # Check if account already exists
        if hasattr(client, 'worker_account'):
            self.stdout.write(self.style.WARNING(f'Worker account already exists for {client.full_name}'))
            return

        if not pin:
            pin = default_worker_pin_from_phone(client.phone)

        account = WorkerAccount(
            client=client,
            phone=client.phone,
            is_active=portal_on,
            created_by='CLI Command',
        )
        account.set_pin(pin)
        account.save()

        status = 'portal login on' if portal_on else 'portal login off — enable “Portal access” in admin'
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Created worker account for {client.full_name} ({status})\n'
                f'   Phone (saved as digits): {account.phone}\n'
                f'   PIN: {pin}\n'
                f'   Account ID: {account.id}'
            )
        )

        if not portal_on:
            self.stdout.write(
                self.style.WARNING(
                    '⚠️  Workers cannot sign in until an admin checks “Portal access” for this account.'
                )
            )
