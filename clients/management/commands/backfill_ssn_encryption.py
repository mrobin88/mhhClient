"""Encrypt legacy plaintext SSNs after the additive schema migration."""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from clients.encrypted_fields import (
    ENCRYPTED_PREFIX,
    decrypt_sensitive_value,
    encrypt_sensitive_value,
)


class Command(BaseCommand):
    help = 'Encrypt legacy Client.ssn values in place. Safe to run repeatedly.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--batch-size', type=int, default=500)

    def handle(self, *args, **options):
        active_key_id = str(getattr(settings, 'SSN_ACTIVE_KEY_ID', 'v1'))
        if active_key_id not in getattr(settings, 'SSN_ENCRYPTION_KEYS', {}):
            raise CommandError(
                f'Active SSN key {active_key_id!r} is not configured. '
                'Set SSN_ENCRYPTION_KEYS before running the backfill.'
            )

        batch_size = max(1, options['batch_size'])
        encrypted_count = 0
        inspected_count = 0
        last_pk = 0

        while True:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, ssn
                    FROM clients_client
                    WHERE id > %s AND ssn IS NOT NULL AND ssn <> ''
                    ORDER BY id
                    LIMIT %s
                    """,
                    [last_pk, batch_size],
                )
                rows = cursor.fetchall()
            if not rows:
                break

            for client_id, stored_value in rows:
                inspected_count += 1
                last_pk = client_id
                plaintext = decrypt_sensitive_value(stored_value)
                digits = ''.join(character for character in plaintext if character.isdigit())
                if len(digits) != 9:
                    raise CommandError(
                        f'Client {client_id} has an invalid SSN; correct it before backfill.'
                    )
                if stored_value.startswith(ENCRYPTED_PREFIX):
                    continue
                if options['dry_run']:
                    encrypted_count += 1
                    continue

                encrypted = encrypt_sensitive_value(
                    f'{digits[:3]}-{digits[3:5]}-{digits[5:]}'
                )
                with transaction.atomic(), connection.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE clients_client
                        SET ssn = %s, ssn_last4 = %s, ssn_key_id = %s
                        WHERE id = %s
                        """,
                        [encrypted, digits[-4:], active_key_id, client_id],
                    )
                encrypted_count += 1

        mode = 'would encrypt' if options['dry_run'] else 'encrypted'
        self.stdout.write(
            self.style.SUCCESS(
                f'Inspected {inspected_count} SSN rows; {mode} {encrypted_count}.'
            )
        )
