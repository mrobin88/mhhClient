"""Write-only partner referral ingest."""
from __future__ import annotations

from django.db import transaction
from django.db.models import F
from rest_framework import status
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from .partner_auth import PartnerAPIKeyAuthentication
from .models_partners import PartnerApiAuditLog, PartnerReferral
from .phone_utils import normalize_login_phone


class PartnerReferralThrottle(AnonRateThrottle):
    scope = 'partner_referral'


class IsAuthenticatedPartner(BasePermission):
    def has_permission(self, request, view):
        return getattr(request, 'partner', None) is not None


def _client_ip(request) -> str | None:
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()[:45] or None
    return (request.META.get('REMOTE_ADDR') or None)


def _audit(request, *, status_code: int, external_id: str = '', detail: str = ''):
    partner = getattr(request, 'partner', None)
    PartnerApiAuditLog.objects.create(
        partner=partner,
        method=request.method,
        path=request.path[:200],
        status_code=status_code,
        external_id=(external_id or '')[:120],
        detail=(detail or '')[:200],
        ip_address=_client_ip(request),
    )


class PartnerReferralIngestView(APIView):
    """
    POST /api/partners/v1/referrals/

    Create or update a referral by (partner, external_id). No GET.
    """

    authentication_classes = [PartnerAPIKeyAuthentication]
    permission_classes = [IsAuthenticatedPartner]
    throttle_classes = [PartnerReferralThrottle]
    http_method_names = ['post', 'options', 'head']

    ALLOWED_FIELDS = {
        'external_id',
        'first_name',
        'last_name',
        'phone',
        'email',
        'notes',
    }

    def post(self, request):
        partner = request.partner
        data = request.data if isinstance(request.data, dict) else {}

        unknown = set(data.keys()) - self.ALLOWED_FIELDS
        if unknown:
            _audit(request, status_code=400, detail=f'unknown fields: {sorted(unknown)[:5]}')
            return Response(
                {
                    'detail': 'Unknown fields are not accepted.',
                    'allowed': sorted(self.ALLOWED_FIELDS),
                    'unknown': sorted(unknown),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        external_id = str(data.get('external_id') or '').strip()
        first_name = str(data.get('first_name') or '').strip()
        last_name = str(data.get('last_name') or '').strip()
        phone_raw = str(data.get('phone') or '').strip()
        email = str(data.get('email') or '').strip()
        notes = str(data.get('notes') or '').strip()

        errors = {}
        if not external_id:
            errors['external_id'] = 'Required. Use your Airtable record id (or other stable id).'
        if len(external_id) > 120:
            errors['external_id'] = 'Max 120 characters.'
        if not first_name:
            errors['first_name'] = 'Required.'
        if not last_name:
            errors['last_name'] = 'Required.'
        if len(first_name) > 100:
            errors['first_name'] = 'Max 100 characters.'
        if len(last_name) > 100:
            errors['last_name'] = 'Max 100 characters.'
        if len(notes) > 2000:
            errors['notes'] = 'Max 2000 characters.'
        if email and '@' not in email:
            errors['email'] = 'Enter a valid email, or leave blank.'
        if not phone_raw and not email:
            errors['phone'] = 'Provide a phone or an email so staff can follow up.'

        if errors:
            _audit(request, status_code=400, external_id=external_id, detail='validation')
            return Response({'detail': 'Validation failed.', 'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

        phone = normalize_login_phone(phone_raw) if phone_raw else ''
        if phone_raw and not phone:
            phone = phone_raw[:40]

        with transaction.atomic():
            referral, created = PartnerReferral.objects.select_for_update().get_or_create(
                partner=partner,
                external_id=external_id,
                defaults={
                    'first_name': first_name,
                    'last_name': last_name,
                    'phone': phone,
                    'email': email,
                    'notes': notes,
                },
            )
            if not created:
                referral.first_name = first_name
                referral.last_name = last_name
                referral.phone = phone
                referral.email = email
                referral.notes = notes
                referral.save(
                    update_fields=[
                        'first_name',
                        'last_name',
                        'phone',
                        'email',
                        'notes',
                        'updated_at',
                    ]
                )

            type(partner).objects.filter(pk=partner.pk).update(request_count=F('request_count') + 1)

        code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        _audit(
            request,
            status_code=code,
            external_id=external_id,
            detail='created' if created else 'updated',
        )

        return Response(
            {
                'id': referral.id,
                'external_id': referral.external_id,
                'status': referral.status,
                'created': created,
                'message': (
                    'Referral received for staff review.'
                    if created
                    else 'Referral updated (same external_id).'
                ),
            },
            status=code,
        )

    def http_method_not_allowed(self, request, *args, **kwargs):
        _audit(request, status_code=405, detail=request.method)
        return Response(
            {'detail': 'This endpoint is write-only. Use POST.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )
