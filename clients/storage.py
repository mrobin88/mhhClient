"""
Azure Blob Storage configuration for client documents
"""

import os
import logging
from urllib.parse import quote
from django.conf import settings
from storages.backends.azure_storage import AzureStorage
from azure.storage.blob import generate_blob_sas, BlobSasPermissions
from datetime import datetime, timedelta


class AzurePrivateStorage(AzureStorage):
    """
    Custom Azure Blob Storage backend for private client documents
    """
    account_name = os.getenv('AZURE_ACCOUNT_NAME')
    account_key = os.getenv('AZURE_ACCOUNT_KEY')
    azure_container = os.getenv('AZURE_CONTAINER', 'client-docs')
    # Private container: generate short-lived SAS in urls
    expiration_secs = 15 * 60  # 15 minutes
    # Do not overwrite existing files
    overwrite_files = False
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure container is private (no public access)
        self.default_acl = None

    def delete(self, name):
        """Fail-soft delete: if blob is missing or auth fails, do not raise."""
        try:
            return super().delete(name)
        except Exception:
            # Intentionally swallow exceptions to avoid cascading 500s on model deletes
            return None


def generate_document_sas_url(blob_name, expiry_minutes=15):
    """
    Generate a short-lived SAS URL for secure document downloads
    
    Args:
        blob_name (str): The blob name/path in Azure storage
        expiry_minutes (int): Minutes until the SAS URL expires (default: 15)
    
    Returns:
        str: Signed URL for secure download
    """
    account_name = os.getenv('AZURE_ACCOUNT_NAME')
    account_key = os.getenv('AZURE_ACCOUNT_KEY')
    container_name = os.getenv('AZURE_CONTAINER', 'client-docs')
    
    if not all([account_name, account_key]):
        raise ValueError("Azure storage credentials not configured")
    
    # Normalize blob name: strip leading slashes and container prefix if present
    if blob_name.startswith('/'):
        blob_name = blob_name.lstrip('/')
    prefix = f"{container_name}/"
    if blob_name.startswith(prefix):
        blob_name = blob_name[len(prefix):]

    # Generate SAS token
    sas_token = generate_blob_sas(
        account_name=account_name,
        container_name=container_name,
        blob_name=blob_name,
        account_key=account_key,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.utcnow() + timedelta(minutes=expiry_minutes)
    )
    
    # Construct the full URL
    # URL-encode blob path but keep slashes
    encoded_blob_path = quote(blob_name, safe='/')
    blob_url = f"https://{account_name}.blob.core.windows.net/{container_name}/{encoded_blob_path}"
    return f"{blob_url}?{sas_token}"


def get_azure_container_client():
    """
    Get Azure Blob Container client for direct operations
    """
    from azure.storage.blob import BlobServiceClient
    
    account_name = os.getenv('AZURE_ACCOUNT_NAME')
    account_key = os.getenv('AZURE_ACCOUNT_KEY')
    container_name = os.getenv('AZURE_CONTAINER', 'client-docs')
    
    if not all([account_name, account_key]):
        return None
    
    blob_service_client = BlobServiceClient(
        account_url=f"https://{account_name}.blob.core.windows.net",
        credential=account_key
    )
    container_client = blob_service_client.get_container_client(container_name)
    try:
        exists = container_client.exists()
        if not exists:
            logging.getLogger('clients').warning(
                "Azure blob container does not exist: account=%s container=%s",
                account_name,
                container_name,
            )
    except Exception as exc:
        logging.getLogger('clients').warning("Failed to verify Azure container existence: %s", exc)
    return container_client