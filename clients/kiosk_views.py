"""
Public kiosk endpoints: lookup client by phone, submit a self check-in case note.

The static web app cannot write to PostgreSQL directly; it calls these APIs over HTTPS.
"""
from pathlib import Path

from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CaseNote, Client, Document
from .phone_utils import find_all_by_normalized_phone, phone_digits
from .serializers import CaseNoteSerializer
from .throttles import KioskLookupThrottle, KioskSubmitThrottle, KioskUploadThrottle

KIOSK_NOTE_AUTHOR = 'Self check-in (kiosk)'
KIOSK_DOC_UPLOADER = 'Self upload (kiosk)'
KIOSK_ID_DOC_MAX_BYTES = 10 * 1024 * 1024
KIOSK_ID_ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.heic', '.heif', '.pdf'}
KIOSK_RESUME_ALLOWED_EXTENSIONS = {'.pdf', '.doc', '.docx', '.txt'}

# Document types a client may attach to their own record without staff involvement.
SELF_UPLOAD_DOC_TYPES = {
    'id': {
        'title': 'Government Photo ID',
        'extensions': KIOSK_ID_ALLOWED_EXTENSIONS,
        'error': 'Only image files or PDF are allowed for Government Photo ID.',
    },
    'resume': {
        'title': 'Resume',
        'extensions': KIOSK_RESUME_ALLOWED_EXTENSIONS,
        'error': 'Only PDF, Word, or text files are allowed for a resume.',
    },
}


def _resolve_client_for_kiosk(phone_raw, client_id):
    if not phone_digits(phone_raw):
        return None, Response({'detail': 'Enter a phone number.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        cid = int(client_id)
    except (TypeError, ValueError):
        return None, Response({'detail': 'Choose your name from the list.'}, status=status.HTTP_400_BAD_REQUEST)

    qs = find_all_by_normalized_phone(Client.objects.all(), phone_raw)
    client = qs.filter(pk=cid).first()
    if not client:
        return None, Response(
            {'detail': 'Phone number does not match that profile. See staff if you need help.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return client, None


class KioskCheckInLookupView(APIView):
    """POST { phone } -> { clients: [{ id, first_name, last_name }] }"""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [KioskLookupThrottle]

    def post(self, request):
        phone = (request.data.get('phone') or '').strip()
        if not phone_digits(phone):
            return Response({'detail': 'Enter a phone number.'}, status=status.HTTP_400_BAD_REQUEST)

        qs = find_all_by_normalized_phone(Client.objects.all(), phone)
        if not qs.exists():
            return Response(
                {
                    'detail': 'No profile found for this number. Complete new client registration first.',
                    'code': 'not_found',
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        clients = [
            {'id': c.id, 'first_name': c.first_name, 'last_name': c.last_name}
            for c in qs[:50]
        ]
        return Response({'clients': clients})


class KioskCheckInSubmitView(APIView):
    """POST { client_id, phone, visit_reason } -> creates CaseNote (timestamped)."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [KioskSubmitThrottle]

    def post(self, request):
        phone = (request.data.get('phone') or '').strip()
        visit_reason = (request.data.get('visit_reason') or '').strip()
        client_id = request.data.get('client_id')

        if not visit_reason:
            return Response({'detail': 'Please describe the reason for your visit.'}, status=status.HTTP_400_BAD_REQUEST)
        if len(visit_reason) > 4000:
            return Response({'detail': 'That description is too long.'}, status=status.HTTP_400_BAD_REQUEST)
        client, err = _resolve_client_for_kiosk(phone, client_id)
        if err:
            return err

        note = CaseNote.objects.create(
            client=client,
            staff_member=KIOSK_NOTE_AUTHOR,
            note_type='general',
            content=visit_reason,
        )
        return Response(
            {
                'ok': True,
                'client_name': client.full_name,
                'case_note': CaseNoteSerializer(note).data,
            },
            status=status.HTTP_201_CREATED,
        )


class KioskDocumentUploadView(APIView):
    """
    POST multipart { client_id, phone, doc_type, title, file, notes? }.

    Used by the lobby kiosk after check-in and by the signup form once the
    client record exists. Defaults to 'id' for older kiosk callers.
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [KioskUploadThrottle]

    def post(self, request):
        phone = (request.data.get('phone') or '').strip()
        client_id = request.data.get('client_id')
        client, err = _resolve_client_for_kiosk(phone, client_id)
        if err:
            return err

        doc_type = (request.data.get('doc_type') or 'id').strip().lower()
        rules = SELF_UPLOAD_DOC_TYPES.get(doc_type)
        if not rules:
            return Response(
                {'detail': 'That document type cannot be uploaded here.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        upload = request.FILES.get('file')
        if not upload:
            return Response({'detail': 'Select a file to upload.'}, status=status.HTTP_400_BAD_REQUEST)
        if getattr(upload, 'size', 0) > KIOSK_ID_DOC_MAX_BYTES:
            return Response({'detail': 'File is too large. Max size is 10MB.'}, status=status.HTTP_400_BAD_REQUEST)

        ext = Path(getattr(upload, 'name', '') or '').suffix.lower()
        if ext not in rules['extensions']:
            return Response({'detail': rules['error']}, status=status.HTTP_400_BAD_REQUEST)

        title = (request.data.get('title') or '').strip()
        if not title:
            title = rules['title']

        notes = (request.data.get('notes') or '').strip() or None

        # Keep uploads organized by client/type in storage.
        try:
            original = upload.name
            upload.name = f"clients/{client.pk}/{doc_type}/{original}"
        except Exception:
            pass

        existing = Document.objects.filter(client=client, doc_type=doc_type).order_by('-created_at').first()
        if existing:
            existing.title = title[:255]
            existing.file = upload
            existing.uploaded_by = KIOSK_DOC_UPLOADER
            existing.notes = notes
            existing.save()
            doc = existing
            created = False
        else:
            doc = Document.objects.create(
                client=client,
                title=title[:255],
                doc_type=doc_type,
                file=upload,
                uploaded_by=KIOSK_DOC_UPLOADER,
                notes=notes,
            )
            created = True

        if doc_type == 'resume':
            # Point the client's resume field at the same stored file so
            # "has resume" and the staff resume download keep working.
            client.resume.name = doc.file.name
            client.save(update_fields=['resume', 'updated_at'])

        return Response(
            {
                'ok': True,
                'created': created,
                'document_id': doc.pk,
                'title': doc.title,
                'doc_type': doc.doc_type,
                'created_at': doc.created_at,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )
