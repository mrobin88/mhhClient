from django.test import TestCase
from rest_framework.test import APIClient

from .models_partners import Partner, PartnerReferral, hash_partner_api_key


class PartnerReferralIngestTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.partner = Partner.objects.create(name='Acme Outreach', slug='acme')
        self.raw_key = self.partner.set_api_key()
        self.partner.save()
        self.url = '/api/partners/v1/referrals/'

    def test_key_is_hashed(self):
        self.assertEqual(self.partner.api_key_hash, hash_partner_api_key(self.raw_key))
        self.assertTrue(self.partner.api_key_prefix)

    def test_rejects_missing_key(self):
        resp = self.api.post(self.url, {'external_id': 'rec1', 'first_name': 'A', 'last_name': 'B'}, format='json')
        self.assertIn(resp.status_code, (401, 403))

    def test_rejects_get(self):
        resp = self.api.get(self.url, HTTP_AUTHORIZATION=f'Bearer {self.raw_key}')
        self.assertEqual(resp.status_code, 405)

    def test_create_and_idempotent_update(self):
        payload = {
            'external_id': 'recAirtable1',
            'first_name': 'Jordan',
            'last_name': 'Lee',
            'phone': '4155551212',
            'notes': 'Ready for orientation',
        }
        created = self.api.post(
            self.url,
            payload,
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {self.raw_key}',
        )
        self.assertEqual(created.status_code, 201)
        self.assertTrue(created.data['created'])
        self.assertEqual(PartnerReferral.objects.count(), 1)

        payload['notes'] = 'Updated note'
        updated = self.api.post(
            self.url,
            payload,
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {self.raw_key}',
        )
        self.assertEqual(updated.status_code, 200)
        self.assertFalse(updated.data['created'])
        self.assertEqual(PartnerReferral.objects.count(), 1)
        self.assertEqual(PartnerReferral.objects.get().notes, 'Updated note')

        self.partner.refresh_from_db()
        self.assertEqual(self.partner.request_count, 2)

    def test_rejects_unknown_fields(self):
        resp = self.api.post(
            self.url,
            {
                'external_id': 'rec2',
                'first_name': 'A',
                'last_name': 'B',
                'phone': '4155559999',
                'ssn': '123456789',
            },
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {self.raw_key}',
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn('ssn', resp.data.get('unknown', []))

    def test_inactive_partner_rejected(self):
        self.partner.is_active = False
        self.partner.save(update_fields=['is_active'])
        resp = self.api.post(
            self.url,
            {
                'external_id': 'rec3',
                'first_name': 'A',
                'last_name': 'B',
                'email': 'a@example.com',
            },
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {self.raw_key}',
        )
        self.assertEqual(resp.status_code, 401)
