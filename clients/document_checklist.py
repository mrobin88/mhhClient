"""Staff/admin document checklist (DB metadata only — no blob calls)."""

from .citybuild_docs import (
    CITYBUILD_CHECKLIST_ITEMS,
    citybuild_item_present,
    is_citybuild_client,
    present_doc_types_for_client,
)

CLIENT_DOC_CHECKLIST = (
    ('resume', 'Resume'),
    ('id', 'Government ID'),
    ('consent', 'Consent Form'),
    ('intake', 'Intake Form'),
    ('sf_residency', 'Proof of SF Residency'),
    ('hs_diploma', 'HS Diploma / GED'),
    ('photo_release', 'Photo Release'),
)


def staff_document_checklist_for_client(client):
    """On-file / missing list used by staff so they know what to request."""
    present = present_doc_types_for_client(client)
    if is_citybuild_client(client):
        notes_count = client.casenotes.count()
        has_resume = 'resume' in present
        checklist = []
        for panel, code, label, source in CITYBUILD_CHECKLIST_ITEMS:
            on_file = citybuild_item_present(
                code, source, present, has_resume, notes_count,
            )
            sendable = source in {'document', 'resume'} and bool(code)
            checklist.append({
                'value': code or 'casenotes',
                'label': label,
                'panel': panel,
                'present': on_file,
                'sendable': sendable,
            })
    else:
        checklist = [
            {
                'value': code,
                'label': label,
                'panel': '',
                'present': code in present,
                'sendable': True,
            }
            for code, label in CLIENT_DOC_CHECKLIST
        ]

    files = []
    for doc in client.documents.exclude(file='').order_by('-created_at'):
        files.append({
            'id': doc.pk,
            'doc_type': doc.doc_type,
            'doc_type_label': doc.get_doc_type_display(),
            'title': doc.title,
            'uploaded_by': doc.uploaded_by or '',
            'created_at': doc.created_at,
        })

    on_file_count = sum(1 for item in checklist if item['present'])
    return {
        'checklist': checklist,
        'files': files,
        'on_file_count': on_file_count,
        'total_count': len(checklist),
        'missing_count': len(checklist) - on_file_count,
    }
