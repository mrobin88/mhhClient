"""
One-time cleanup command to remove database records for missing Azure blobs
Run once: python manage.py cleanup_missing_docs
"""

from django.core.management.base import BaseCommand
from clients.models import Client, Document


class Command(BaseCommand):
    help = 'Remove database records for files that do not exist in Azure Blob Storage'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== CLEANING UP MISSING FILE REFERENCES ===\n'))
        
        # Clear Client 27's missing resume
        try:
            client_27 = Client.objects.get(id=27)
            self.stdout.write(f"Clearing resume for {client_27.full_name}: {client_27.resume.name}")
            client_27.resume = None
            client_27.save()
            self.stdout.write(self.style.SUCCESS('✅ Cleared Client 27 resume'))
        except Client.DoesNotExist:
            self.stdout.write(self.style.WARNING('⚠ Client 27 not found'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Error with Client 27: {e}'))
        
        # Clear Client 24's missing resume
        try:
            client_24 = Client.objects.get(id=24)
            self.stdout.write(f"Clearing resume for {client_24.full_name}: {client_24.resume.name}")
            client_24.resume = None
            client_24.save()
            self.stdout.write(self.style.SUCCESS('✅ Cleared Client 24 resume'))
        except Client.DoesNotExist:
            self.stdout.write(self.style.WARNING('⚠ Client 24 not found'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Error with Client 24: {e}'))
        
        # Delete Doc 6 (missing file)
        try:
            doc_6 = Document.objects.get(id=6)
            self.stdout.write(f"Deleting document: {doc_6.title} - {doc_6.file.name}")
            doc_6.delete()
            self.stdout.write(self.style.SUCCESS('✅ Deleted Doc 6'))
        except Document.DoesNotExist:
            self.stdout.write(self.style.WARNING('⚠ Doc 6 not found'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Error with Doc 6: {e}'))
        
        self.stdout.write(self.style.SUCCESS('\n=== CLEANUP COMPLETE ===\n'))
