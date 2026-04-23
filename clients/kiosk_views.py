"""
Public kiosk endpoints: lookup client by phone, submit a self check-in case note.

The static web app cannot write to PostgreSQL directly; it calls these APIs over HTTPS.
"""
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CaseNote, Client, Document
from .phone_utils import find_all_by_normalized_phone, phone_digits
from .serializers import CaseNoteSerializer

KIOSK_NOTE_AUTHOR = 'Self check-in (kiosk)'
KIOSK_DOC_UPLOADER = 'Self upload (kiosk)'


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
    Lets returning clients add missing documents after check-in.
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        phone = (request.data.get('phone') or '').strip()
        client_id = request.data.get('client_id')
        client, err = _resolve_client_for_kiosk(phone, client_id)
        if err:
            return err

        upload = request.FILES.get('file')
        if not upload:
            return Response({'detail': 'Select a file to upload.'}, status=status.HTTP_400_BAD_REQUEST)

        doc_type = (request.data.get('doc_type') or 'other').strip()
        valid_doc_types = {v for v, _ in Document.DOC_TYPE_CHOICES}
        if doc_type not in valid_doc_types:
            return Response({'detail': 'Invalid document type.'}, status=status.HTTP_400_BAD_REQUEST)

        title = (request.data.get('title') or '').strip()
        if not title:
            title = dict(Document.DOC_TYPE_CHOICES).get(doc_type, 'Uploaded Document')

        notes = (request.data.get('notes') or '').strip() or None

        # Keep uploads organized by client/type in storage.
        try:
            original = upload.name
            upload.name = f"clients/{client.pk}/{doc_type}/{original}"
        except Exception:
            pass

        doc = Document.objects.create(
            client=client,
            title=title[:255],
            doc_type=doc_type,
            file=upload,
            uploaded_by=KIOSK_DOC_UPLOADER,
            notes=notes,
        )

        return Response(
            {
                'ok': True,
                'document_id': doc.pk,
                'title': doc.title,
                'doc_type': doc.doc_type,
                'created_at': doc.created_at,
            },
            status=status.HTTP_201_CREATED,
        )
