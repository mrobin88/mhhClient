"""Bearer API key auth for partner ingest endpoints."""
from __future__ import annotations

from rest_framework import authentication, exceptions

from .models_partners import Partner, hash_partner_api_key


class PartnerAPIKeyAuthentication(authentication.BaseAuthentication):
    """
    Authorization: Bearer <api_key>
    Also accepts X-Api-Key: <api_key>
    """

    keyword = 'Bearer'

    def authenticate(self, request):
        raw = self._extract_key(request)
        if not raw:
            raise exceptions.NotAuthenticated(
                'Provide Authorization: Bearer <api_key> (or X-Api-Key).'
            )

        partner = Partner.objects.filter(
            is_active=True,
            api_key_hash=hash_partner_api_key(raw),
        ).first()
        if partner is None:
            raise exceptions.AuthenticationFailed('Invalid or inactive partner API key.')

        request.partner = partner
        return (None, partner)

    def authenticate_header(self, request):
        return self.keyword

    def _extract_key(self, request) -> str:
        header = request.META.get('HTTP_AUTHORIZATION', '')
        if header:
            parts = header.split()
            if len(parts) == 2 and parts[0] == self.keyword:
                return parts[1].strip()
            if len(parts) == 1 and parts[0].startswith('mhh_pk_'):
                return parts[0].strip()

        return request.META.get('HTTP_X_API_KEY', '').strip()
