"""
Quick command to create worker accounts for PitStop clients
Run: python manage.py quick_add_worker
"""

from django.core.management.base import BaseCommand
from clients.models import Client
from clients.models_extensions import WorkerAccount
from django.contrib.auth.hashers import make_password


class Command(BaseCommand):
    help = 'Quick add worker accounts for PitStop clients without existing accounts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--phone',
            type=str,
            help='Create account for specific phone number only',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Create accounts for ALL PitStop clients without accounts',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== QUICK ADD WORKER ACCOUNTS ===\n'))
        
        # Find PitStop clients
        pitstop_clients = Client.objects.filter(training_interest='pit_stop')
        
        if options['phone']:
            # Create for specific phone
            phone = options['phone'].strip()
            try:
                client = pitstop_clients.get(phone=phone)
            except Client.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'✗ No PitStop client found with phone: {phone}'))
                return
            
            clients_to_process = [client]
        elif options['all']:
            # Create for all without accounts
            clients_to_process = [c for c in pitstop_clients if not hasattr(c, 'worker_account')]
        else:
            # Interactive mode - show list
            clients_without_accounts = [c for c in pitstop_clients if not hasattr(c, 'worker_account')]
            
            if not clients_without_accounts:
                self.stdout.write(self.style.WARNING('✓ All PitStop clients already have worker accounts!'))
                return
            
            self.stdout.write(f'Found {len(clients_without_accounts)} PitStop clients without worker accounts:\n')
            for idx, client in enumerate(clients_without_accounts, 1):
                self.stdout.write(f'  {idx}. {client.full_name} - {client.phone}')
            
            self.stdout.write('\nOptions:')
            self.stdout.write('  --phone PHONE    Create for specific phone')
            self.stdout.write('  --all            Create for all listed above')
            return
        
        # Create accounts
        created_count = 0
        for client in clients_to_process:
            if hasattr(client, 'worker_account'):
                self.stdout.write(self.style.WARNING(f'⚠ {client.full_name} already has a worker account'))
                continue
            
            # Generate PIN from last 4 digits of phone
            pin = client.phone[-4:] if len(client.phone) >= 4 else '1234'
            
            # Create worker account
            worker_account = WorkerAccount.objects.create(
                client=client,
                phone=client.phone,
                pin_hash=make_password(pin),
                is_active=True,
                is_approved=True,
                created_by='Quick Add Command'
            )
            
            self.stdout.write(self.style.SUCCESS(
                f'✓ Created worker account for {client.full_name}\n'
                f'  Phone: {client.phone}\n'
                f'  PIN: {pin} (last 4 of phone)\n'
            ))
            created_count += 1
        
        if created_count > 0:
            self.stdout.write(self.style.SUCCESS(f'\n✓ Created {created_count} worker account(s)'))
            self.stdout.write('\nWorkers can now login at:')
            self.stdout.write('  https://blue-glacier-0c5f06410.3.azurestaticapps.net/worker/')
        else:
            self.stdout.write(self.style.WARNING('\n⚠ No new accounts created'))
