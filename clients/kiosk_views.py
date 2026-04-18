"""
Public kiosk endpoints: lookup client by phone, submit a self check-in case note.

The static web app cannot write to PostgreSQL directly; it calls these APIs over HTTPS.
"""
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CaseNote, Client
from .phone_utils import find_all_by_normalized_phone, phone_digits
from .serializers import CaseNoteSerializer

KIOSK_NOTE_AUTHOR = 'Self check-in (kiosk)'


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

        if not phone_digits(phone):
            return Response({'detail': 'Enter a phone number.'}, status=status.HTTP_400_BAD_REQUEST)
        if not visit_reason:
            return Response({'detail': 'Please describe the reason for your visit.'}, status=status.HTTP_400_BAD_REQUEST)
        if len(visit_reason) > 4000:
            return Response({'detail': 'That description is too long.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cid = int(client_id)
        except (TypeError, ValueError):
            return Response({'detail': 'Choose your name from the list.'}, status=status.HTTP_400_BAD_REQUEST)

        qs = find_all_by_normalized_phone(Client.objects.all(), phone)
        client = qs.filter(pk=cid).first()
        if not client:
            return Response(
                {'detail': 'Phone number does not match that profile. See staff if you need help.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

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
