"""
Azure Blob Storage configuration for client documents
"""

import os
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
    azure_container = 'client-docs'
    expiration_secs = None  # No public access
    overwrite_files = False  # Don't overwrite existing files
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure container is private (no public access)
        self.default_acl = None


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
    container_name = 'client-docs'
    
    if not all([account_name, account_key]):
        raise ValueError("Azure storage credentials not configured")
    
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
    blob_url = f"https://{account_name}.blob.core.windows.net/{container_name}/{blob_name}"
    return f"{blob_url}?{sas_token}"


def get_azure_container_client():
    """
    Get Azure Blob Container client for direct operations
    """
    from azure.storage.blob import BlobServiceClient
    
    account_name = os.getenv('AZURE_ACCOUNT_NAME')
    account_key = os.getenv('AZURE_ACCOUNT_KEY')
    
    if not all([account_name, account_key]):
        return None
    
    blob_service_client = BlobServiceClient(
        account_url=f"https://{account_name}.blob.core.windows.net",
        credential=account_key
    )
    
    return blob_service_client.get_container_client('client-docs')