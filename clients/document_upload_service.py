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

# Cheap Android cameras often send image/jpeg with no filename suffix.
CONTENT_TYPE_EXTENSIONS = {
    'image/jpeg': '.jpg',
    'image/jpg': '.jpg',
    'image/pjpeg': '.jpg',
    'image/png': '.png',
    'image/webp': '.webp',
    'image/heic': '.heic',
    'image/heif': '.heif',
    'image/gif': '.gif',
    'application/pdf': '.pdf',
    'application/msword': '.doc',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
    'text/plain': '.txt',
}


def _upload_content_type(upload):
    return (getattr(upload, 'content_type', '') or '').split(';')[0].strip().lower()


def _upload_extension(upload):
    return Path(getattr(upload, 'name', '') or '').suffix.lower()


def validate_self_upload(upload, *, allowed_extensions=None):
    if not upload:
        return 'Select a file to upload.'
    if getattr(upload, 'size', 0) <= 0:
        return 'That file appears to be empty.'
    allowed = allowed_extensions or IMAGE_OR_DOCUMENT_EXTENSIONS
    extension = _upload_extension(upload)
    if extension in allowed:
        return None
    content_type = _upload_content_type(upload)
    inferred = CONTENT_TYPE_EXTENSIONS.get(content_type, '')
    if content_type.startswith('image/') and not inferred:
        inferred = '.jpg'
    if inferred and inferred in allowed:
        return None
    # Some phone browsers send a camera shot as octet-stream with no filename.
    if not extension and content_type in ('', 'application/octet-stream', 'application/x-octet-stream'):
        if '.jpg' in allowed or '.jpeg' in allowed:
            return None
    return 'Only images, PDF, Word, or text files are allowed.'


def save_client_document(*, client, doc_type, upload, uploaded_by, title=None, notes=None):
    """Create or replace the latest document of this type for a client."""
    labels = dict(Document.DOC_TYPE_CHOICES)
    title = (title or labels.get(doc_type) or 'Client document')[:255]
    original = Path(getattr(upload, 'name', '') or 'upload.bin').name[:120]
    if not Path(original).suffix:
        inferred = CONTENT_TYPE_EXTENSIONS.get(_upload_content_type(upload), '')
        if not inferred and (
            _upload_content_type(upload).startswith('image/')
            or _upload_content_type(upload) in ('', 'application/octet-stream', 'application/x-octet-stream')
        ):
            inferred = '.jpg'
        if inferred:
            original = f'{(original or "upload").rstrip(".")}{inferred}'
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
