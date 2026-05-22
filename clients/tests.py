import shutil
import tempfile
from datetime import date, time
from unittest.mock import patch

from django.contrib.admin.sites import AdminSite
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from clients.admin import ClientAdmin
from clients.models import Client
from clients.models import Document
from clients.notifications import _to_e164_us, _compose_sms_body, send_phone_text_message
from clients.models_extensions import WorkerAccount, WorkerShiftProof, WorkAssignment, WorkSite, ClientTextMessage
from clients.worker_views import WorkerSession


TEST_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class WorkerShiftProofTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.api = APIClient()
        self.client_record = Client.objects.create(
            first_name='Test',
            last_name='Worker',
            phone='4155551212',
            email='worker@example.com',
            gender='M',
            training_interest='pit_stop',
            status='active',
        )
        self.worker = WorkerAccount(
            client=self.client_record,
            phone='4155551212',
            worker_status=WorkerAccount.STATUS_ACTIVE,
        )
        self.worker.set_pin('1212')
        self.worker.save()
        self.site = WorkSite.objects.create(
            name='Mission Pit Stop',
            address='123 Mission St',
            typical_start_time=time(8, 0),
            typical_end_time=time(16, 0),
        )
        self.assignment = WorkAssignment.objects.create(
            client=self.client_record,
            work_site=self.site,
            assignment_date=date.today(),
            start_time=time(8, 0),
            end_time=time(16, 0),
            status='confirmed',
            assigned_by='Admin',
        )
        token = WorkerSession.create_session(self.worker)
        self.api.credentials(HTTP_AUTHORIZATION=f'Token {token}')

    def test_worker_can_submit_photo_and_location_proof(self):
        photo = SimpleUploadedFile(
            'proof.jpg',
            b'fake image bytes',
            content_type='image/jpeg',
        )

        response = self.api.post(
            '/api/worker/shift-proof/',
            {
                'assignment_id': self.assignment.pk,
                'photo': photo,
                'geolocation': (
                    '{"status":"captured","latitude":37.7749,'
                    '"longitude":-122.4194,"accuracy":25,'
                    '"timestamp":"2026-05-13T20:00:00Z"}'
                ),
            },
            format='multipart',
        )

        self.assertEqual(response.status_code, 201)
        proof = WorkerShiftProof.objects.get()
        self.assertEqual(proof.worker_account, self.worker)
        self.assertEqual(proof.assignment, self.assignment)
        self.assertTrue(proof.photo.name)
        self.assertEqual(proof.geo_status, 'captured')
        self.assertTrue(proof.geo_basic_ok)

    def test_worker_assignments_include_latest_photo_proof(self):
        WorkerShiftProof.objects.create(
            worker_account=self.worker,
            assignment=self.assignment,
            photo=SimpleUploadedFile('proof.jpg', b'fake image bytes', content_type='image/jpeg'),
            geo_status='captured',
            geo_basic_ok=True,
            geo_basic_note='Captured with accuracy 25m',
        )

        response = self.api.get('/api/worker/assignments/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertTrue(response.data[0]['proof_submitted'])
        self.assertIsNotNone(response.data[0]['latest_proof'])

    def test_legacy_time_punch_endpoint_is_gone(self):
        response = self.api.post('/api/worker/time-punch/', {'action': 'clock_in'}, format='json')

        self.assertEqual(response.status_code, 410)


class ClientAdminTextMissingDocumentsTests(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.admin = ClientAdmin(Client, self.site)
        self.client_record = Client.objects.create(
            first_name='Missing',
            last_name='Docs',
            phone='4155552222',
            email='missing@example.com',
            gender='F',
        )

    @override_settings(
        AZURE_COMMUNICATION_CONNECTION_STRING='endpoint=https://example.test/;accesskey=fake',
        AZURE_COMMUNICATION_SMS_FROM='+15555550123',
    )
    @patch('clients.notifications.send_text_message')
    def test_text_missing_documents_action_sends_sms_for_clients_with_missing_required_docs(self, send_text_mock):
        class Log:
            status = ClientTextMessage.STATUS_SENT

        send_text_mock.return_value = (Log(), True)

        # Only intake is present; resume/id/consent should still be requested.
        Document.objects.create(
            client=self.client_record,
            title='Intake Form',
            doc_type='intake',
            file=SimpleUploadedFile('intake.pdf', b'pdf', content_type='application/pdf'),
            uploaded_by='staff',
        )

        request = type('Req', (), {'user': None})()
        with patch.object(self.admin, 'message_user'):
            self.admin.text_missing_documents(request, Client.objects.filter(pk=self.client_record.pk))

        send_text_mock.assert_called_once()
        kwargs = send_text_mock.call_args.kwargs
        self.assertEqual(kwargs['client'], self.client_record)
        self.assertIn('Resume', kwargs['body'])
        self.assertIn('Government ID', kwargs['body'])
        self.assertIn('Consent Form', kwargs['body'])
        self.assertNotIn('Intake Form', kwargs['body'])


class SmsPhoneFormattingTests(TestCase):
    def test_to_e164_us_formats_common_us_phone_inputs(self):
        self.assertEqual(_to_e164_us('(925) 550-7522'), '+19255507522')
        self.assertEqual(_to_e164_us('+1 (925) 550-7522'), '+19255507522')
        self.assertEqual(_to_e164_us('925-550-7522 ext 14'), '+19255507522')
        self.assertEqual(_to_e164_us('1-925-550-7522 x99'), '+19255507522')

    def test_to_e164_us_rejects_invalid_short_values(self):
        self.assertEqual(_to_e164_us('925-550'), '')

    @override_settings(SMS_APPEND_COMPLIANCE_FOOTER=True, SMS_COMPLIANCE_FOOTER=' Reply STOP to opt out.')
    def test_compose_sms_body_appends_footer(self):
        body = _compose_sms_body('Mission Hiring Hall update.')
        self.assertTrue(body.endswith('Reply STOP to opt out.'))


class SmsInternalOnlyGuardrailTests(TestCase):
    def setUp(self):
        self.client_record = Client.objects.create(
            first_name='Allowed',
            last_name='Recipient',
            phone='9255501111',
            email='allowed@example.com',
            gender='F',
        )

    @override_settings(SMS_INTERNAL_ONLY=True)
    def test_internal_only_blocks_unknown_phone(self):
        ok, detail = send_phone_text_message(phone='9255509999', body='Test')
        self.assertFalse(ok)
        self.assertIn('allowlisted', detail)

    @override_settings(SMS_INTERNAL_ONLY=True, AZURE_COMMUNICATION_CONNECTION_STRING='endpoint=https://example.test/;accesskey=fake', AZURE_COMMUNICATION_SMS_FROM='+15555550123')
    @patch('clients.notifications._sms_client')
    def test_internal_only_allows_known_phone(self, sms_client_mock):
        class SmsResult:
            successful = True
            message_id = 'msg-123'

        sms_client_mock.return_value.send.return_value = [SmsResult()]
        ok, detail = send_phone_text_message(phone='9255501111', body='Test')
        self.assertTrue(ok)
        self.assertIn('+19255501111', detail)
