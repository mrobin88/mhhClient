import shutil
import tempfile
from datetime import date, time, timedelta  # date used for note_date tests
from unittest.mock import patch

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.test import Client as DjangoTestClient
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from clients.admin import ClientAdmin
from clients.models import Client
from clients.models import Document
from clients.notifications import _to_e164_us, _compose_sms_body, send_phone_text_message
from clients.models_extensions import WorkerAccount, WorkerTimePunch, WorkSite, ClientTextMessage
from clients.worker_views import WorkerSession


TEST_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class WorkerTimePunchTests(TestCase):
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
            latitude=37.7749,
            longitude=-122.4194,
            typical_start_time=time(8, 0),
            typical_end_time=time(16, 0),
        )
        token = WorkerSession.create_session(self.worker)
        self.api.credentials(HTTP_AUTHORIZATION=f'Token {token}')

    def test_worker_can_list_active_work_sites(self):
        response = self.api.get('/api/worker/work-sites/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.site.id)

    def test_worker_can_clock_in_without_work_site(self):
        """Worker portal no longer sends work_site_id — punch still records and
        geo lat/long are still saved for audit. Geofence check is skipped."""
        response = self.api.post(
            '/api/worker/time-punch/',
            {
                'action': 'clock_in',
                'geolocation': (
                    '{"status":"captured","latitude":37.7800,'
                    '"longitude":-122.4100,"accuracy":18,'
                    '"timestamp":"2026-05-28T19:00:00Z"}'
                ),
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        punch = WorkerTimePunch.objects.get()
        self.assertEqual(punch.worker_account, self.worker)
        self.assertIsNone(punch.work_site)
        self.assertEqual(punch.clock_in_geo_status, 'captured')
        # lat/long must still land in the DB for staff audit even without a site.
        self.assertIsNotNone(punch.clock_in_latitude)
        self.assertIsNotNone(punch.clock_in_longitude)
        # Without a site we grade on format/precision only, which passes here.
        self.assertTrue(punch.clock_in_geo_basic_ok)

    def test_worker_can_clock_in_with_geolocation(self):
        response = self.api.post(
            '/api/worker/time-punch/',
            {
                'action': 'clock_in',
                'work_site_id': self.site.pk,
                'geolocation': (
                    '{"status":"captured","latitude":37.7749,'
                    '"longitude":-122.4194,"accuracy":25,'
                    '"timestamp":"2026-05-13T20:00:00Z"}'
                ),
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        punch = WorkerTimePunch.objects.get()
        self.assertEqual(punch.worker_account, self.worker)
        self.assertEqual(punch.work_site, self.site)
        self.assertEqual(punch.clock_in_geo_status, 'captured')
        self.assertTrue(punch.clock_in_geo_basic_ok)
        self.assertIsNone(punch.clock_out_at)

    def test_worker_clock_context_includes_active_punch(self):
        WorkerTimePunch.objects.create(
            worker_account=self.worker,
            work_site=self.site,
            clock_in_at=timezone.now(),
            clock_in_geo_status='captured',
            clock_in_geo_basic_ok=True,
            clock_in_geo_basic_note='Captured with accuracy 25m',
        )

        response = self.api.get('/api/worker/time-punch/')

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.data['active_punch'])
        self.assertEqual(len(response.data['punches']), 1)
        self.assertIn('today_hours', response.data)
        self.assertIn('week_hours', response.data)

    def test_worker_clock_context_returns_completed_hours_summary(self):
        # Two completed punches today: 2h + 1.5h. Open punches excluded.
        now = timezone.now().replace(microsecond=0)
        WorkerTimePunch.objects.create(
            worker_account=self.worker,
            work_site=self.site,
            clock_in_at=now - timedelta(hours=6),
            clock_out_at=now - timedelta(hours=4),
            clock_in_geo_status='captured',
            clock_in_geo_basic_ok=True,
        )
        WorkerTimePunch.objects.create(
            worker_account=self.worker,
            work_site=self.site,
            clock_in_at=now - timedelta(hours=3),
            clock_out_at=now - timedelta(hours=1, minutes=30),
            clock_in_geo_status='captured',
            clock_in_geo_basic_ok=True,
        )
        # Open punch should NOT contribute to today_hours (server returns completed only).
        WorkerTimePunch.objects.create(
            worker_account=self.worker,
            work_site=self.site,
            clock_in_at=now - timedelta(minutes=30),
            clock_in_geo_status='captured',
            clock_in_geo_basic_ok=True,
        )

        response = self.api.get('/api/worker/time-punch/')

        self.assertEqual(response.status_code, 200)
        # 2h + 1.5h = 3.5 hours. Allow tiny rounding wiggle.
        self.assertAlmostEqual(float(response.data['today_hours']), 3.5, places=2)
        self.assertAlmostEqual(float(response.data['week_hours']), 3.5, places=2)
        self.assertIsNotNone(response.data['active_punch'])

    def test_worker_can_clock_out(self):
        punch = WorkerTimePunch.objects.create(
            worker_account=self.worker,
            work_site=self.site,
            clock_in_at=timezone.now(),
            clock_in_geo_status='captured',
            clock_in_geo_basic_ok=True,
            clock_in_geo_basic_note='Captured with accuracy 25m',
        )

        response = self.api.post(
            '/api/worker/time-punch/',
            {
                'action': 'clock_out',
                'work_site_id': self.site.pk,
                'geolocation': (
                    '{"status":"captured","latitude":37.7749,'
                    '"longitude":-122.4194,"accuracy":25,'
                    '"timestamp":"2026-05-13T20:30:00Z"}'
                ),
            },
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        punch.refresh_from_db()
        self.assertIsNotNone(punch.clock_out_at)
        self.assertEqual(punch.clock_out_geo_status, 'captured')
        self.assertTrue(punch.clock_out_geo_basic_ok)

    def test_worker_lunch_flow_subtracts_from_net_hours(self):
        # Clock in 8h ago.
        punch = WorkerTimePunch.objects.create(
            worker_account=self.worker,
            clock_in_at=timezone.now() - timedelta(hours=8),
            clock_in_geo_status='captured',
            clock_in_geo_basic_ok=True,
        )
        geo = (
            '{"status":"captured","latitude":37.7749,'
            '"longitude":-122.4194,"accuracy":20,'
            '"timestamp":"2026-05-28T19:00:00Z"}'
        )

        start = self.api.post(
            '/api/worker/time-punch/',
            {'action': 'start_lunch', 'geolocation': geo},
            format='json',
        )
        self.assertEqual(start.status_code, 200)
        punch.refresh_from_db()
        self.assertTrue(punch.is_on_lunch)
        self.assertIsNotNone(punch.lunch_start_latitude)

        # Can't clock out while on lunch.
        blocked = self.api.post(
            '/api/worker/time-punch/',
            {'action': 'clock_out', 'geolocation': geo},
            format='json',
        )
        self.assertEqual(blocked.status_code, 400)
        self.assertIn('lunch', blocked.data['error'].lower())

        # End lunch, then make it a 30-min lunch for deterministic math.
        end = self.api.post(
            '/api/worker/time-punch/',
            {'action': 'end_lunch', 'geolocation': geo},
            format='json',
        )
        self.assertEqual(end.status_code, 200)
        punch.refresh_from_db()
        punch.lunch_start_at = punch.clock_out_at or timezone.now()
        # Force a known 30-minute lunch window.
        punch.lunch_start_at = timezone.now() - timedelta(hours=4)
        punch.lunch_end_at = punch.lunch_start_at + timedelta(minutes=30)
        punch.clock_out_at = punch.clock_in_at + timedelta(hours=8)
        punch.save()
        punch.refresh_from_db()
        self.assertEqual(punch.lunch_minutes, 30)
        # 8h worked − 0.5h lunch = 7.5h net.
        self.assertAlmostEqual(punch.net_hours, 7.5, places=2)

    def test_start_lunch_requires_clock_in(self):
        response = self.api.post(
            '/api/worker/time-punch/',
            {
                'action': 'start_lunch',
                'geolocation': (
                    '{"status":"captured","latitude":37.7749,'
                    '"longitude":-122.4194,"accuracy":20}'
                ),
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def _login_superuser(self):
        User = get_user_model()
        admin_user = User.objects.create_superuser(
            username='timepunch_admin',
            email='admin@example.com',
            password='supersecure123!',
        )
        client = DjangoTestClient()
        assert client.login(username=admin_user.username, password='supersecure123!')
        return client

    def test_pitstop_hours_csv_includes_completed_punch(self):
        clock_in = timezone.now().replace(microsecond=0) - timedelta(hours=5)
        clock_out = clock_in + timedelta(hours=4, minutes=30)
        WorkerTimePunch.objects.create(
            worker_account=self.worker,
            work_site=self.site,
            clock_in_at=clock_in,
            clock_out_at=clock_out,
            clock_in_geo_status='captured',
            clock_in_geo_basic_ok=True,
            clock_in_geo_basic_note='Captured with accuracy 20m',
            clock_out_geo_status='captured',
            clock_out_geo_basic_ok=True,
            clock_out_geo_basic_note='Captured with accuracy 22m',
            clock_in_latitude=37.7749,
            clock_in_longitude=-122.4194,
            clock_out_latitude=37.7749,
            clock_out_longitude=-122.4194,
        )

        client = self._login_superuser()
        url = reverse('pitstop-hours-report-csv')
        response = client.get(url)

        self.assertEqual(response.status_code, 200)
        body = response.content.decode('utf-8')
        header = body.strip().splitlines()[0]
        # Accountant-friendly column order leads with the worker name.
        self.assertTrue(header.startswith('Worker Name,Date,Clock In,'))
        self.assertIn('Hours', body)
        self.assertIn('Status', body)
        self.assertIn('Test Worker', body)
        self.assertIn('Mission Pit Stop', body)
        self.assertIn('4.50', body)
        self.assertIn('Complete', body)

    def test_pitstop_hours_csv_skips_open_punch_when_only_complete(self):
        WorkerTimePunch.objects.create(
            worker_account=self.worker,
            work_site=self.site,
            clock_in_at=timezone.now() - timedelta(hours=1),
            clock_in_geo_status='captured',
            clock_in_geo_basic_ok=True,
            clock_in_geo_basic_note='Captured with accuracy 18m',
        )

        client = self._login_superuser()
        response = client.get(reverse('pitstop-hours-report-csv') + '?only_complete=1')

        self.assertEqual(response.status_code, 200)
        body = response.content.decode('utf-8')
        rows = [line for line in body.strip().splitlines() if line]
        self.assertEqual(len(rows), 1)
        self.assertIn('Worker Name', rows[0])

    @override_settings(
        STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage',
        STORAGES={
            'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
            'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
        },
    )
    def test_worker_time_punch_admin_change_list_shows_compact_columns(self):
        WorkerTimePunch.objects.create(
            worker_account=self.worker,
            work_site=self.site,
            clock_in_at=timezone.now() - timedelta(hours=2),
            clock_out_at=timezone.now(),
            clock_in_geo_status='captured',
            clock_in_geo_basic_ok=True,
            clock_in_geo_basic_note='Captured with accuracy 20m',
            clock_out_geo_status='captured',
            clock_out_geo_basic_ok=False,
            clock_out_geo_basic_note='Outside site geofence (300m > 183m)',
        )

        client = self._login_superuser()
        response = client.get('/admin/clients/workertimepunch/')

        self.assertEqual(response.status_code, 200)
        body = response.content.decode('utf-8')
        self.assertIn('Hours', body)
        self.assertIn('Geofence', body)


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
        SMS_FORCE_EMAIL_BACKUP=True,
    )
    @patch('clients.notifications.send_text_message')
    @patch('clients.admin.send_mail')
    def test_text_missing_documents_action_sends_sms_for_clients_with_missing_required_docs(self, send_mail_mock, send_text_mock):
        class Log:
            status = ClientTextMessage.STATUS_SENT

        send_text_mock.return_value = (Log(), True)
        send_mail_mock.return_value = 1

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
        send_mail_mock.assert_called_once()


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


@override_settings(
    MEDIA_ROOT=TEST_MEDIA_ROOT,
    STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage',
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    },
)
class ClientAdminChangeViewTests(TestCase):
    """Client admin change must not HEAD-check every Azure blob on page load."""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create_superuser(
            username='admin',
            password='testpass123',
            email='admin@example.com',
        )
        self.django_client = DjangoTestClient()
        self.django_client.force_login(self.staff)
        self.client_record = Client.objects.create(
            first_name='Davis',
            last_name='Example',
            phone='4155559999',
            email='davis@example.com',
            gender='M',
            training_interest='general',
            status='active',
        )
        self.client_record.resume = SimpleUploadedFile('resume.pdf', b'%PDF-1.4 resume')
        self.client_record.save()
        for idx in range(8):
            Document.objects.create(
                client=self.client_record,
                title=f'Document {idx}',
                doc_type='other',
                file=SimpleUploadedFile(f'doc{idx}.jpg', b'jpeg-bytes'),
                uploaded_by='admin',
            )

    @patch('clients.storage.blob_exists')
    def test_client_change_page_loads_without_azure_blob_checks(self, blob_exists_mock):
        url = reverse('admin:clients_client_change', args=[self.client_record.pk])
        response = self.django_client.get(url)
        self.assertEqual(response.status_code, 200)
        blob_exists_mock.assert_not_called()
        self.assertContains(response, 'documents hub')
        self.assertContains(response, 'Document checklist')
        self.assertNotContains(response, 'Supporting Documents')

    def test_client_documents_hub_lists_files_without_blob_checks(self):
        url = reverse('admin:clients_client_documents', args=[self.client_record.pk])
        with patch('clients.storage.blob_exists') as blob_exists_mock:
            response = self.django_client.get(url)
        self.assertEqual(response.status_code, 200)
        blob_exists_mock.assert_not_called()
        self.assertContains(response, 'Download')
        self.assertContains(response, 'Government ID')

    def test_case_note_inline_includes_editable_note_date(self):
        from clients.models import CaseNote
        CaseNote.objects.create(
            client=self.client_record,
            staff_member='admin',
            note_type='general',
            content='Retro entry',
            note_date=date(2025, 9, 2),
        )
        url = reverse('admin:clients_client_change', args=[self.client_record.pk])
        response = self.django_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'note_date')
        self.assertContains(response, '2025-09-02')

    def test_client_change_with_worker_account_renders_portal_summary(self):
        from clients.models_extensions import WorkerAccount
        WorkerAccount.objects.create(
            client=self.client_record,
            phone='4155551111',
            pin_hash='test',
            is_active=True,
        )
        url = reverse('admin:clients_client_change', args=[self.client_record.pk])
        response = self.django_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Worker portal summary')
        self.assertContains(response, 'View time punches')
        self.assertNotContains(response, 'workassignment_set-group')

    def test_client_change_caps_case_note_inline_rows(self):
        from clients.models import CaseNote
        for idx in range(45):
            CaseNote.objects.create(
                client=self.client_record,
                staff_member='admin',
                note_type='general',
                content=f'Note {idx}',
                note_date=date(2025, 1, 1) + timedelta(days=idx),
            )
        url = reverse('admin:clients_client_change', args=[self.client_record.pk])
        response = self.django_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'View all 45 case notes')
        self.assertContains(response, 'Only the 40 most recent notes')
