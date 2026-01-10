"""
Azure Blob Storage configuration for client documents
"""

import os
import logging
from urllib.parse import quote
from django.conf import settings
from storages.backends.azure_storage import AzureStorage
from azure.storage.blob import generate_blob_sas, BlobSasPermissions
from datetime import datetime, timedelta, timezone


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
    
    # Remove container prefix if present
    prefix = f"{container_name}/"
    if blob_name.startswith(prefix):
        blob_name = blob_name[len(prefix):]
    
    logger = logging.getLogger('clients')
    logger.info('Generating SAS URL for blob_name: %s (container: %s)', blob_name, container_name)

    # Try multiple path variations to handle different storage patterns
    # 1. Try exact path as stored
    # 2. Try with resumes/ prefix (for Client.resume uploads)
    # 3. Try with documents/ prefix (for Document.file uploads)
    # 4. Try without any prefix (direct blob name)
    
    paths_to_try = [
        blob_name,  # Original path
    ]
    
    # Add alternative paths based on the original
    if blob_name.startswith('documents/'):
        paths_to_try.append(blob_name.replace('documents/', 'resumes/', 1))
        paths_to_try.append(blob_name.replace('documents/', '', 1))  # Remove prefix
    elif blob_name.startswith('resumes/'):
        paths_to_try.append(blob_name.replace('resumes/', 'documents/', 1))
        paths_to_try.append(blob_name.replace('resumes/', '', 1))  # Remove prefix
    else:
        # No prefix - try adding both
        paths_to_try.append(f'resumes/{blob_name}')
        paths_to_try.append(f'documents/{blob_name}')
    
    # Remove duplicates while preserving order
    seen = set()
    unique_paths = []
    for path in paths_to_try:
        if path not in seen:
            seen.add(path)
            unique_paths.append(path)
    
    # Try each path until one works
    last_error = None
    for attempt_path in unique_paths:
        try:
            logger.info('Attempting SAS generation for path: %s', attempt_path)
            # Use timezone-aware UTC datetime to avoid clock skew issues
            now = datetime.now(timezone.utc)
            expiry_time = now + timedelta(minutes=expiry_minutes)
            
            sas_token = generate_blob_sas(
                account_name=account_name,
                container_name=container_name,
                blob_name=attempt_path,
                account_key=account_key,
                permission=BlobSasPermissions(read=True),
                expiry=expiry_time
            )
            
            # Construct the full URL
            encoded_blob_path = quote(attempt_path, safe='/')
            blob_url = f"https://{account_name}.blob.core.windows.net/{container_name}/{encoded_blob_path}"
            logger.info('Successfully generated SAS URL for path: %s', attempt_path)
            return f"{blob_url}?{sas_token}"
        except Exception as e:
            last_error = e
            logger.debug('Path %s failed: %s', attempt_path, e)
            continue
    
    # All paths failed
    logger.error('All blob path attempts failed for %s. Last error: %s', blob_name, last_error)
    raise ValueError(f"Could not generate SAS URL for blob. Tried paths: {unique_paths}. Last error: {last_error}")


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