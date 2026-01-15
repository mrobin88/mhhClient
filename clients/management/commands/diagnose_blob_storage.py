"""
Django management command to diagnose Azure Blob Storage issues
Run: python manage.py diagnose_blob_storage
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from clients.models import Client, Document
from azure.storage.blob import BlobServiceClient
import os


class Command(BaseCommand):
    help = 'Diagnose Azure Blob Storage configuration and document paths'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== AZURE BLOB STORAGE DIAGNOSTICS ===\n'))
        
        # Check configuration
        self.stdout.write(self.style.WARNING('1. Configuration Check:'))
        self.stdout.write(f"   DEFAULT_FILE_STORAGE: {settings.DEFAULT_FILE_STORAGE}")
        
        account_name = os.getenv('AZURE_ACCOUNT_NAME')
        account_key = os.getenv('AZURE_ACCOUNT_KEY')
        container_name = os.getenv('AZURE_CONTAINER', 'client-docs')
        
        self.stdout.write(f"   AZURE_ACCOUNT_NAME: {'✓ SET' if account_name else '✗ NOT SET'}")
        self.stdout.write(f"   AZURE_ACCOUNT_KEY: {'✓ SET' if account_key else '✗ NOT SET'}")
        self.stdout.write(f"   AZURE_CONTAINER: {container_name}")
        
        if not account_name or not account_key:
            self.stdout.write(self.style.ERROR('\n✗ Azure credentials not configured!'))
            self.stdout.write('  Set AZURE_ACCOUNT_NAME and AZURE_ACCOUNT_KEY environment variables.')
            return
        
        # Check database records
        self.stdout.write(self.style.WARNING('\n2. Database Records:'))
        
        clients_with_resumes = Client.objects.exclude(resume='').exclude(resume__isnull=True)
        self.stdout.write(f"   Clients with resumes: {clients_with_resumes.count()}")
        for client in clients_with_resumes[:5]:
            self.stdout.write(f"     • Client {client.id} ({client.full_name}): {client.resume.name}")
        
        documents = Document.objects.all()
        self.stdout.write(f"   Documents: {documents.count()}")
        for doc in documents[:5]:
            self.stdout.write(f"     • Doc {doc.id} ({doc.title}): {doc.file.name}")
        
        # Check Azure Blob Storage
        self.stdout.write(self.style.WARNING('\n3. Azure Blob Storage Contents:'))
        
        try:
            blob_service = BlobServiceClient(
                account_url=f"https://{account_name}.blob.core.windows.net",
                credential=account_key
            )
            container_client = blob_service.get_container_client(container_name)
            
            # Check if container exists
            if not container_client.exists():
                self.stdout.write(self.style.ERROR(f'   ✗ Container "{container_name}" does not exist!'))
                return
            
            self.stdout.write(f'   ✓ Container "{container_name}" exists')
            
            # List all blobs
            blobs = list(container_client.list_blobs())
            self.stdout.write(f'   Total blobs: {len(blobs)}')
            
            if blobs:
                self.stdout.write('\n   Blob paths:')
                for blob in blobs[:10]:
                    size_kb = blob.size / 1024
                    self.stdout.write(f'     • {blob.name} ({size_kb:.1f} KB)')
                
                if len(blobs) > 10:
                    self.stdout.write(f'     ... and {len(blobs) - 10} more')
            else:
                self.stdout.write(self.style.WARNING('   ⚠ No blobs found in container!'))
            
            # Compare database paths with actual blobs
            self.stdout.write(self.style.WARNING('\n4. Path Mismatch Analysis:'))
            
            blob_paths = set(blob.name for blob in blobs)
            
            # Check client resumes
            mismatches = []
            for client in clients_with_resumes:
                db_path = client.resume.name
                if db_path not in blob_paths:
                    # Try common variations
                    variations = [
                        db_path,
                        f'client-docs/{db_path}',
                        db_path.replace('client-docs/', ''),
                        db_path.replace('documents/', 'resumes/'),
                        db_path.replace('resumes/', 'documents/'),
                    ]
                    found = None
                    for variation in variations:
                        if variation in blob_paths:
                            found = variation
                            break
                    
                    if found:
                        mismatches.append((f'Client {client.id}', db_path, found))
                    else:
                        mismatches.append((f'Client {client.id}', db_path, 'NOT FOUND'))
            
            # Check documents
            for doc in documents:
                db_path = doc.file.name
                if db_path not in blob_paths:
                    variations = [
                        db_path,
                        f'client-docs/{db_path}',
                        db_path.replace('client-docs/', ''),
                        db_path.replace('documents/', 'resumes/'),
                        db_path.replace('resumes/', 'documents/'),
                    ]
                    found = None
                    for variation in variations:
                        if variation in blob_paths:
                            found = variation
                            break
                    
                    if found:
                        mismatches.append((f'Doc {doc.id}', db_path, found))
                    else:
                        mismatches.append((f'Doc {doc.id}', db_path, 'NOT FOUND'))
            
            if mismatches:
                self.stdout.write(self.style.ERROR(f'   ✗ Found {len(mismatches)} mismatches:'))
                for record, db_path, actual_path in mismatches[:10]:
                    if actual_path == 'NOT FOUND':
                        self.stdout.write(f'     • {record}: DB={db_path} → BLOB=NOT FOUND ❌')
                    else:
                        self.stdout.write(f'     • {record}: DB={db_path} → BLOB={actual_path} ⚠')
                
                if len(mismatches) > 10:
                    self.stdout.write(f'     ... and {len(mismatches) - 10} more mismatches')
            else:
                self.stdout.write(self.style.SUCCESS('   ✓ All database paths match Azure blobs!'))
            
            self.stdout.write(self.style.SUCCESS('\n=== DIAGNOSTICS COMPLETE ===\n'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n✗ Error accessing Azure Blob Storage: {e}'))
            import traceback
            self.stdout.write(traceback.format_exc())
