"""Staff-issued, public document upload invitations."""

from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db.models import F
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .document_upload_service import save_client_document, validate_self_upload
from .citybuild_docs import CITYBUILD_UPLOAD_DOC_TYPES, is_citybuild_client, present_doc_types_for_client
from .models import Client, Document, DocumentUploadInvite
from .notifications import send_text_message
from .staff_auth import StaffSessionAuthentication
from .throttles import UploadInviteThrottle


def _invite_from_token(token):
    if not token:
        return None
    return (
        DocumentUploadInvite.objects.select_related('client')
        .filter(token_hash=DocumentUploadInvite.hash_token(token))
        .first()
    )


def _public_invite_payload(invite):
    labels = dict(Document.DOC_TYPE_CHOICES)
    return {
        'first_name': invite.client.first_name,
        'documents': [
            {'value': value, 'label': labels.get(value, value)}
            for value in invite.allowed_doc_types
        ],
        'expires_at': invite.expires_at,
        'uploads_remaining': max(invite.max_uploads - invite.upload_count, 0),
    }


@api_view(['GET', 'POST'])
@authentication_classes([StaffSessionAuthentication])
@permission_classes([IsAuthenticated])
def staff_client_upload_invites(request, pk):
    if not request.user.is_staff:
        return Response({'error': 'Staff access required.'}, status=status.HTTP_403_FORBIDDEN)
    try:
        client = Client.objects.get(pk=pk)
    except Client.DoesNotExist:
        return Response({'error': 'Client not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        invitations = client.document_upload_invites.all()[:20]
        options = (
            CITYBUILD_UPLOAD_DOC_TYPES
            if is_citybuild_client(client)
            else Document.DOC_TYPE_CHOICES
        )
        present = present_doc_types_for_client(client)
        return Response({
            'document_options': [
                {'value': value, 'label': label}
                for value, label in options
            ],
            'suggested_doc_types': [
                value for value, _label in options
                if value not in present and value != 'other'
            ],
            'results': [
                {
                    'id': invite.pk,
                    'token_prefix': invite.token_prefix,
                    'allowed_doc_types': invite.allowed_doc_types,
                    'expires_at': invite.expires_at,
                    'upload_count': invite.upload_count,
                    'revoked_at': invite.revoked_at,
                    'is_usable': invite.is_usable,
                    'created_at': invite.created_at,
                }
                for invite in invitations
            ]
        })

    allowed_values = dict(Document.DOC_TYPE_CHOICES)
    requested = request.data.get('doc_types') or []
    if not isinstance(requested, list):
        return Response({'doc_types': ['Choose one or more document types.']}, status=400)
    doc_types = list(dict.fromkeys(str(value) for value in requested if value in allowed_values))
    if not doc_types:
        return Response({'doc_types': ['Choose one or more valid document types.']}, status=400)
    try:
        expires_days = min(max(int(request.data.get('expires_days') or 14), 1), 30)
    except (TypeError, ValueError):
        return Response({'expires_days': ['Choose a number from 1 to 30.']}, status=400)

    invite, raw_token = DocumentUploadInvite.issue(
        client=client,
        allowed_doc_types=doc_types,
        created_by=request.user,
        expires_at=timezone.now() + timedelta(days=expires_days),
    )
    base_url = getattr(settings, 'PUBLIC_APP_BASE_URL', '').rstrip('/')
    link = f'{base_url}/upload/{raw_token}'
    delivery = str(request.data.get('delivery') or 'copy')
    delivery_detail = ''
    message = (
        f'Hi {client.first_name}, use this secure Mission Hiring Hall link to upload '
        f'your requested documents by {invite.expires_at:%b %d}: {link}'
    )
    if delivery == 'email':
        if not client.email:
            invite.delete()
            return Response({'email': ['This client does not have an email address.']}, status=400)
        send_mail(
            'Secure document upload link',
            message,
            settings.DEFAULT_FROM_EMAIL,
            [client.email],
            fail_silently=False,
        )
        delivery_detail = f'Email sent to {client.email}.'
    elif delivery == 'sms':
        log, _ = send_text_message(
            client,
            message,
            purpose='general',
            dedupe_key=f'document-upload-invite:{invite.pk}',
            require_enabled_flag=False,
        )
        if log.status == log.STATUS_FAILED:
            invite.delete()
            return Response({'delivery': [log.error_message or 'Text message failed.']}, status=400)
        delivery_detail = f'Text sent to {client.phone}.'

    return Response(
        {
            'id': invite.pk,
            'link': link,
            'expires_at': invite.expires_at,
            'allowed_doc_types': invite.allowed_doc_types,
            'delivery_detail': delivery_detail,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(['POST'])
@authentication_classes([StaffSessionAuthentication])
@permission_classes([IsAuthenticated])
def staff_upload_invite_revoke(request, invite_id):
    if not request.user.is_staff:
        return Response({'error': 'Staff access required.'}, status=status.HTTP_403_FORBIDDEN)
    try:
        invite = DocumentUploadInvite.objects.get(pk=invite_id)
    except DocumentUploadInvite.DoesNotExist:
        return Response({'error': 'Upload link not found.'}, status=status.HTTP_404_NOT_FOUND)
    if invite.revoked_at is None:
        invite.revoked_at = timezone.now()
        invite.save(update_fields=['revoked_at'])
    return Response({'message': 'Upload link revoked.'})


class PublicDocumentUploadInviteView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [UploadInviteThrottle]

    def get(self, request, token):
        invite = _invite_from_token(token)
        if not invite or not invite.is_usable:
            return Response({'detail': 'This upload link is invalid or has expired.'}, status=410)
        return Response(_public_invite_payload(invite))

    def post(self, request, token):
        invite = _invite_from_token(token)
        if not invite or not invite.is_usable:
            return Response({'detail': 'This upload link is invalid or has expired.'}, status=410)
        doc_type = str(request.data.get('doc_type') or '')
        if doc_type not in invite.allowed_doc_types:
            return Response({'detail': 'That document was not requested on this link.'}, status=400)
        upload = request.FILES.get('file')
        upload_error = validate_self_upload(upload)
        if upload_error:
            return Response({'detail': upload_error}, status=400)

        document, created = save_client_document(
            client=invite.client,
            doc_type=doc_type,
            upload=upload,
            uploaded_by=f'Self upload (invite {invite.token_prefix})',
        )
        DocumentUploadInvite.objects.filter(pk=invite.pk).update(
            upload_count=F('upload_count') + 1,
            last_used_at=timezone.now(),
        )
        return Response(
            {
                'ok': True,
                'created': created,
                'document_id': document.pk,
                'doc_type': document.doc_type,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )
