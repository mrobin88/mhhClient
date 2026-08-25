"""Shared validation and persistence for client self-service uploads."""

import logging
from pathlib import Path
from uuid import uuid4

from .models import Document

logger = logging.getLogger('clients')


IMAGE_OR_DOCUMENT_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.webp', '.heic', '.heif',
    '.pdf', '.doc', '.docx', '.txt',
}


def validate_self_upload(upload, *, allowed_extensions=None):
    if not upload:
        return 'Select a file to upload.'
    if getattr(upload, 'size', 0) <= 0:
        return 'That file appears to be empty.'
    extension = Path(getattr(upload, 'name', '') or '').suffix.lower()
    if extension not in (allowed_extensions or IMAGE_OR_DOCUMENT_EXTENSIONS):
        return 'Only images, PDF, Word, or text files are allowed.'
    return None


def save_client_document(*, client, doc_type, upload, uploaded_by, title=None, notes=None):
    """Create or replace the latest document of this type for a client."""
    labels = dict(Document.DOC_TYPE_CHOICES)
    title = (title or labels.get(doc_type) or 'Client document')[:255]
    original = Path(getattr(upload, 'name', '') or 'upload.bin').name[:120]
    try:
        # Unique blob names so a retry / replace does not collide with
        # AzurePrivateStorage.overwrite_files = False.
        upload.name = f'clients/{client.pk}/{doc_type}/{uuid4().hex}_{original}'
    except Exception:
        pass

    document = (
        Document.objects.filter(client=client, doc_type=doc_type)
        .order_by('-created_at')
        .first()
    )
    created = document is None
    if created:
        document = Document(client=client, doc_type=doc_type)
    document.title = title
    document.file = upload
    document.uploaded_by = uploaded_by
    document.notes = notes or None
    document.save()

    if doc_type == 'resume':
        try:
            client.resume.name = document.file.name
            client.save(update_fields=['resume', 'updated_at'])
        except Exception:
            # The file is already on the Document row. Do not fail the upload
            # because mirroring onto Client.resume hit an unrelated field.
            logger.exception(
                'Resume stored on Document but Client.resume could not be updated client=%s',
                client.pk,
            )
    return document, created
