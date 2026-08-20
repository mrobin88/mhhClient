"""Shared validation and persistence for client self-service uploads."""

from pathlib import Path

from .models import Document


MAX_SELF_UPLOAD_BYTES = 10 * 1024 * 1024
IMAGE_OR_DOCUMENT_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.webp', '.heic', '.heif',
    '.pdf', '.doc', '.docx', '.txt',
}


def validate_self_upload(upload, *, allowed_extensions=None):
    if not upload:
        return 'Select a file to upload.'
    if getattr(upload, 'size', 0) <= 0:
        return 'That file appears to be empty.'
    if getattr(upload, 'size', 0) > MAX_SELF_UPLOAD_BYTES:
        return 'File is too large. Max size is 10MB.'
    extension = Path(getattr(upload, 'name', '') or '').suffix.lower()
    if extension not in (allowed_extensions or IMAGE_OR_DOCUMENT_EXTENSIONS):
        return 'Only images, PDF, Word, or text files are allowed.'
    return None


def save_client_document(*, client, doc_type, upload, uploaded_by, title=None, notes=None):
    """Create or replace the latest document of this type for a client."""
    labels = dict(Document.DOC_TYPE_CHOICES)
    title = (title or labels.get(doc_type) or 'Client document')[:255]
    try:
        upload.name = f'clients/{client.pk}/{doc_type}/{upload.name}'
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
        client.resume.name = document.file.name
        client.save(update_fields=['resume', 'updated_at'])
    return document, created
