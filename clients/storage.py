"""
Azure Blob Storage configuration for client documents
"""

import os
import logging
from urllib.parse import quote
from django.conf import settings
from storages.backends.azure_storage import AzureStorage
from azure.storage.blob import generate_blob_sas, BlobSasPermissions, BlobServiceClient
from datetime import datetime, timedelta, timezone

logger = logging.getLogger('clients')


class AzurePrivateStorage(AzureStorage):
    """
    Custom Azure Blob Storage backend for private client documents
    """
    account_name = os.getenv('AZURE_ACCOUNT_NAME')
    account_key = os.getenv('AZURE_ACCOUNT_KEY')
    azure_container = os.getenv('AZURE_CONTAINER', 'client-docs')
    expiration_secs = 15 * 60  # 15-minute SAS tokens
    overwrite_files = False
    location = ''
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.default_acl = None

    def delete(self, name):
        """Fail-soft delete: log but don't crash if blob is already gone."""
        try:
            return super().delete(name)
        except Exception as exc:
            logger.warning('Blob delete failed for %s (may already be gone): %s', name, exc)
            return None


def _get_blob_service():
    """Get Azure BlobServiceClient, or None if not configured."""
    account_name = os.getenv('AZURE_ACCOUNT_NAME')
    account_key = os.getenv('AZURE_ACCOUNT_KEY')
    if not account_name or not account_key:
        return None, None, None
    container_name = os.getenv('AZURE_CONTAINER', 'client-docs')
    service = BlobServiceClient(
        account_url=f"https://{account_name}.blob.core.windows.net",
        credential=account_key
    )
    return service, account_name, container_name


def blob_exists(blob_name):
    """Check if a blob exists in Azure Storage. Returns the found path or None."""
    service, account_name, container_name = _get_blob_service()
    if not service:
        return None
    
    container = service.get_container_client(container_name)

    # Normalize: strip leading slash and container prefix
    blob_name = blob_name.lstrip('/')
    prefix = f"{container_name}/"
    if blob_name.startswith(prefix):
        blob_name = blob_name[len(prefix):]

    # Build list of paths to try (exact first, then variations)
    paths = [blob_name]
    if blob_name.startswith('documents/'):
        paths.append(blob_name.replace('documents/', 'resumes/', 1))
        paths.append(blob_name.replace('documents/', '', 1))
    elif blob_name.startswith('resumes/'):
        paths.append(blob_name.replace('resumes/', 'documents/', 1))
        paths.append(blob_name.replace('resumes/', '', 1))
    else:
        paths.extend([f'resumes/{blob_name}', f'documents/{blob_name}'])

    for path in dict.fromkeys(paths):  # dedupe, preserve order
        try:
            if container.get_blob_client(path).exists():
                return path
        except Exception:
            continue
    return None


def generate_document_sas_url(blob_name, expiry_minutes=15):
    """
    Generate a short-lived SAS URL for secure document downloads.
    Returns a signed URL string, or raises ValueError with a clear message.
    """
    service, account_name, container_name = _get_blob_service()
    if not service:
        raise ValueError("Azure storage credentials not configured. Check AZURE_ACCOUNT_NAME and AZURE_ACCOUNT_KEY.")

    found_path = blob_exists(blob_name)
    if not found_path:
        raise FileNotFoundError(
            f"File not found in Azure Storage. "
            f"The file '{blob_name}' does not exist in the '{container_name}' container. "
            f"Please re-upload the file."
        )

    now = datetime.now(timezone.utc)
    sas_token = generate_blob_sas(
        account_name=account_name,
        container_name=container_name,
        blob_name=found_path,
        account_key=os.getenv('AZURE_ACCOUNT_KEY'),
        permission=BlobSasPermissions(read=True),
        start=now - timedelta(minutes=5),
        expiry=now + timedelta(minutes=expiry_minutes),
    )

    encoded = quote(found_path, safe='/')
    return f"https://{account_name}.blob.core.windows.net/{container_name}/{encoded}?{sas_token}"


def verify_upload(blob_name):
    """
    After saving a file, verify it actually made it to Azure.
    Returns True if blob exists, False otherwise.
    """
    return blob_exists(blob_name) is not None


def get_azure_container_client():
    """Get Azure Blob Container client for admin/diagnostic operations."""
    service, account_name, container_name = _get_blob_service()
    if not service:
        return None
    container = service.get_container_client(container_name)
    try:
        if not container.exists():
            logger.warning("Azure container does not exist: %s/%s", account_name, container_name)
    except Exception as exc:
        logger.warning("Failed to verify Azure container: %s", exc)
    return container