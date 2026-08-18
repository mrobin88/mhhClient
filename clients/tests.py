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
from clients.models import CaseNote, Client
from clients.models import Document, PitStopApplication
from clients.models_classes import ClassEnrollment, ClassSession, ClassTemplate
from clients.notifications import _to_e164_us, _compose_sms_body, send_phone_text_message
from clients.models_extensions import (
    ClientTextMessage,
    WorkerAccount,
    WorkerDailyFeedback,
    WorkerTimePunch,
    WorkSite,
)
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

    @patch('clients.worker_views.fetch_static_map_image')
    def test_worker_can_clock_in_with_location_snapshot(self, map_mock):
        from django.core.files.base import ContentFile

        map_mock.return_value = ContentFile(b'fakepng', name='map.png')
        response = self.api.post(
            '/api/worker/time-punch/',
            {
                'action': 'clock_in',
                'location_label': 'Mission St & 16th St',
                'map_latitude': '37.7749',
                'map_longitude': '-122.4194',
            },
            format='multipart',
        )

        self.assertEqual(response.status_code, 201)
        punch = WorkerTimePunch.objects.get()
        self.assertEqual(punch.worker_account, self.worker)
        self.assertEqual(punch.clock_in_location_label, 'Mission St & 16th St')
        self.assertTrue(bool(punch.clock_in_map_image))
        self.assertIsNone(punch.clock_out_at)

    def test_worker_clock_in_requires_location_services(self):
        response = self.api.post(
            '/api/worker/time-punch/',
            {'action': 'clock_in'},
            format='multipart',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('location', response.data['error'].lower())

    def test_worker_can_clock_in_with_explicit_work_site(self):
        response = self.api.post(
            '/api/worker/time-punch/',
            {
                'action': 'clock_in',
                'work_site_id': self.site.pk,
                'geolocation': (
                    '{"status":"captured","latitude":37.7749,'
                    '"longitude":-122.4194,"accuracy":20}'
                ),
            },
            format='multipart',
        )
        self.assertEqual(response.status_code, 201)
        punch = WorkerTimePunch.objects.get()
        self.assertEqual(punch.work_site, self.site)

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

    def test_start_lunch_requires_location_services(self):
        WorkerTimePunch.objects.create(
            worker_account=self.worker,
            clock_in_at=timezone.now() - timedelta(hours=2),
            clock_in_geo_status='captured',
            clock_in_geo_basic_ok=True,
        )
        response = self.api.post(
            '/api/worker/time-punch/',
            {'action': 'start_lunch'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('location', response.data['error'].lower())

    def test_worker_can_submit_simple_incident_report(self):
        response = self.api.post(
            '/api/worker/incident-report/',
            {
                'occurred_at': '2026-06-25T09:30',
                'involved_people': 'Customer and Pit Stop worker',
                'brief_description': 'Customer slipped near the sink.',
                'what_happened': 'Customer slipped near the sink and we cleaned it.',
                'where_happened': 'Restroom sink area',
                'why_happened': 'Water on the floor',
                'actions_taken': 'Checked on customer and cleaned the floor.',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        note = CaseNote.objects.latest('created_at')
        self.assertEqual(note.client_id, self.client_record.id)
        self.assertIn('Worker Incident Report', note.content)
        self.assertIn(f'Reporting person: {self.client_record.full_name}', note.content)
        self.assertIn('When it happened: 2026-06-25T09:30', note.content)

    def test_worker_incident_report_requires_fields(self):
        response = self.api.post(
            '/api/worker/incident-report/',
            {
                'occurred_at': '',
                'involved_people': '',
                'brief_description': '',
                'what_happened': '',
                'where_happened': '',
                'why_happened': '',
                'actions_taken': '',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('occurred_at', response.data)
        self.assertIn('involved_people', response.data)

    def test_worker_can_update_profile_goals(self):
        response = self.api.patch(
            '/api/worker/profile/update/',
            {
                'short_profile': 'I like customer-facing work and team environments.',
                'long_term_career_goals': 'I want to become a lead supervisor.',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.worker.refresh_from_db()
        self.assertIn('team environments', self.worker.short_profile)
        self.assertIn('lead supervisor', self.worker.long_term_career_goals)

    def test_worker_daily_feedback_upserts_for_today(self):
        create_response = self.api.post(
            '/api/worker/daily-feedback/',
            {'feedback_text': 'Good day, but needed more gloves.'},
            format='json',
        )
        self.assertEqual(create_response.status_code, 201)
        self.assertEqual(WorkerDailyFeedback.objects.count(), 1)

        update_response = self.api.post(
            '/api/worker/daily-feedback/',
            {'feedback_text': 'Update: supplies arrived and shift ended smoothly.'},
            format='json',
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(WorkerDailyFeedback.objects.count(), 1)

        feedback = WorkerDailyFeedback.objects.get(worker_account=self.worker)
        self.assertIn('supplies arrived', feedback.feedback_text)

    def test_worker_daily_feedback_get_returns_recent_entries(self):
        WorkerDailyFeedback.objects.create(
            worker_account=self.worker,
            feedback_date=timezone.localdate() - timedelta(days=1),
            feedback_text='Yesterday feedback entry',
        )
        WorkerDailyFeedback.objects.create(
            worker_account=self.worker,
            feedback_date=timezone.localdate(),
            feedback_text='Today feedback entry',
        )
        response = self.api.get('/api/worker/daily-feedback/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['today_feedback']['feedback_text'], 'Today feedback entry')
        self.assertGreaterEqual(len(response.data['recent_feedback']), 2)

    def test_worker_dashboard_summary_includes_incident_counts(self):
        CaseNote.objects.create(
            client=self.client_record,
            staff_member='Worker Portal',
            note_type='general',
            content='Worker Incident Report\nSupervisor: Test\nWhat happened: One',
        )
        CaseNote.objects.create(
            client=self.client_record,
            staff_member='Worker Portal',
            note_type='general',
            content='Worker Incident Report\nSupervisor: Test\nWhat happened: Two',
        )
        WorkerDailyFeedback.objects.create(
            worker_account=self.worker,
            feedback_date=timezone.localdate(),
            feedback_text='Daily check-in',
        )
        response = self.api.get('/api/worker/dashboard-summary/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['incident_reports_today'], 2)
        self.assertTrue(response.data['has_feedback_today'])

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

    def test_pitstop_hours_printable_html_for_fiscal_review(self):
        clock_in = timezone.now().replace(microsecond=0) - timedelta(hours=5)
        clock_out = clock_in + timedelta(hours=4, minutes=30)
        WorkerTimePunch.objects.create(
            worker_account=self.worker,
            work_site=self.site,
            clock_in_at=clock_in,
            clock_out_at=clock_out,
            clock_in_geo_status='captured',
            clock_in_geo_basic_ok=True,
            clock_out_geo_status='captured',
            clock_out_geo_basic_ok=True,
        )
        client = self._login_superuser()
        response = client.get(reverse('pitstop-hours-printable') + '?only_complete=1')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/html; charset=utf-8')
        body = response.content.decode('utf-8')
        self.assertIn('Mission Hiring Hall', body)
        self.assertIn('By worker (for payroll review)', body)
        self.assertIn('Test Worker', body)
        self.assertIn('4.50', body)

    def test_pitstop_hours_package_zip_downloads(self):
        clock_in = timezone.now().replace(microsecond=0) - timedelta(hours=3)
        clock_out = clock_in + timedelta(hours=2)
        WorkerTimePunch.objects.create(
            worker_account=self.worker,
            work_site=self.site,
            clock_in_at=clock_in,
            clock_out_at=clock_out,
            clock_in_geo_status='captured',
            clock_in_geo_basic_ok=True,
            clock_out_geo_status='captured',
            clock_out_geo_basic_ok=True,
        )
        client = self._login_superuser()
        response = client.get(reverse('pitstop-hours-package') + '?only_complete=1')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/zip')

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
        self.assertIn('Location', body)


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
        SMS_FOLLOWUP_ENABLED=True,
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

    @override_settings(
        AZURE_COMMUNICATION_CONNECTION_STRING='endpoint=https://example.test/;accesskey=fake',
        AZURE_COMMUNICATION_SMS_FROM='+15555550123',
        SMS_FOLLOWUP_ENABLED=False,
    )
    @patch('clients.notifications.send_text_message')
    def test_reminder_texts_stay_off_so_class_signup_is_the_only_text(self, send_text_mock):
        request = type('Req', (), {'user': None})()
        with patch.object(self.admin, 'message_user') as message_user:
            self.admin.text_missing_documents(request, Client.objects.filter(pk=self.client_record.pk))

        send_text_mock.assert_not_called()
        self.assertIn('turned off', message_user.call_args.args[1])


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

    def test_citybuild_client_change_uses_slim_files_section(self):
        self.client_record.training_interest = 'citybuild'
        self.client_record.save(update_fields=['training_interest'])
        url = reverse('admin:clients_client_change', args=[self.client_record.pk])
        response = self.django_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'City Build Files')
        self.assertContains(response, 'City Build files hub')
        self.assertNotContains(response, 'Panel 1')
        self.assertNotContains(response, 'Upload client resume')

    def test_capsa_client_change_has_no_academy_checklist(self):
        self.client_record.training_interest = 'capsa'
        self.client_record.save(update_fields=['training_interest'])
        url = reverse('admin:clients_client_change', args=[self.client_record.pk])
        response = self.django_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'City Build Files')
        self.assertNotContains(response, 'City Build files hub')

    def test_citybuild_checklist_admin_changelist(self):
        self.client_record.training_interest = 'citybuild'
        self.client_record.save(update_fields=['training_interest'])
        url = reverse('admin:clients_citybuildfilechecklist_changelist')
        response = self.django_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Davis Example')

    def test_worker_account_add_uses_client_autocomplete(self):
        self.client_record.training_interest = 'pit_stop'
        self.client_record.save(update_fields=['training_interest'])
        add_url = reverse('admin:clients_workeraccount_add')
        response = self.django_client.get(add_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'autocomplete')
        self.assertNotContains(response, 'is_available')

        ac_response = self.django_client.get(
            '/admin/autocomplete/',
            {
                'term': 'Davis',
                'app_label': 'clients',
                'model_name': 'workeraccount',
                'field_name': 'client',
            },
        )
        self.assertEqual(ac_response.status_code, 200)
        self.assertContains(ac_response, 'Davis')

        Client.objects.create(
            first_name='General',
            last_name='Only',
            phone='4155558888',
            gender='M',
            training_interest='general',
        )
        ac_response = self.django_client.get(
            '/admin/autocomplete/',
            {
                'term': 'Davis',
                'app_label': 'clients',
                'model_name': 'workeraccount',
                'field_name': 'client',
            },
        )
        self.assertNotContains(ac_response, 'General Only')

    def test_citybuild_documents_hub_uses_panel_checklist(self):
        self.client_record.training_interest = 'citybuild'
        self.client_record.save(update_fields=['training_interest'])
        Document.objects.create(
            client=self.client_record,
            title='TABE scan',
            doc_type='cb_tabe',
            file=SimpleUploadedFile('tabe.pdf', b'%PDF tabe'),
            uploaded_by='admin',
        )
        url = reverse('admin:clients_client_documents', args=[self.client_record.pk])
        with patch('clients.storage.blob_exists') as blob_exists_mock:
            response = self.django_client.get(url)
        self.assertEqual(response.status_code, 200)
        blob_exists_mock.assert_not_called()
        self.assertContains(response, 'City Build files')
        self.assertContains(response, 'TABE')
        self.assertContains(response, 'Received')
        self.assertContains(response, 'Staff sign-off')

    def test_citybuild_tile_upload_marks_checklist_received(self):
        from clients.citybuild_docs import citybuild_packet_for_client
        self.client_record.training_interest = 'citybuild'
        self.client_record.save(update_fields=['training_interest'])
        url = reverse('admin:clients_client_documents', args=[self.client_record.pk])
        response = self.django_client.post(
            url,
            {
                'action': 'upload_checklist_item',
                'checklist_source': 'document',
                'doc_type': 'cb_tabe',
                'file': SimpleUploadedFile('tabe.pdf', b'%PDF tabe'),
            },
        )
        self.assertEqual(response.status_code, 302)
        packet = citybuild_packet_for_client(self.client_record)
        tabe_present = any(label == 'TABE' and present for label, present in packet['items'])
        self.assertTrue(tabe_present)
        follow = self.django_client.get(url)
        self.assertContains(follow, 'TABE')
        self.assertContains(follow, 'Received')

    def test_citybuild_confirmation_checkbox_optional(self):
        self.client_record.training_interest = 'citybuild'
        self.client_record.save(update_fields=['training_interest'])
        url = reverse('admin:clients_client_documents', args=[self.client_record.pk])
        response = self.django_client.post(url, {
            'action': 'save_confirmation',
            'citybuild_confirmed': '1',
        })
        self.assertEqual(response.status_code, 302)
        self.client_record.refresh_from_db()
        self.assertTrue(self.client_record.citybuild_files_confirmed)
        self.assertEqual(self.client_record.citybuild_files_confirmed_by, 'admin')

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


class ClientStaffAutoAssignTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.case_manager = User.objects.create_user(
            username='cmaria',
            password='testpass123',
            first_name='Maria',
            last_name='Lopez',
            role='case_manager',
            is_staff=True,
        )
        self.admin_user = User.objects.create_user(
            username='adminrole',
            password='testpass123',
            first_name='Admin',
            last_name='User',
            role='admin',
            is_staff=True,
        )
        self.client_record = Client.objects.create(
            first_name='Assign',
            last_name='Test',
            phone='4155550001',
            email='assign@example.com',
            gender='M',
            training_interest='general',
            status='active',
            staff_name='Original Manager',
        )
        self.api = APIClient()

    def test_admin_save_model_reassigns_on_update(self):
        from django.test import RequestFactory
        from clients.admin import ClientAdmin

        request = RequestFactory().get('/')
        request.user = self.case_manager
        admin = ClientAdmin(Client, AdminSite())
        obj = Client.objects.get(pk=self.client_record.pk)
        admin.save_model(request, obj, form=None, change=True)
        obj.save()
        obj.refresh_from_db()
        self.assertEqual(obj.staff_name, 'Maria Lopez')

    def test_admin_save_model_skips_admin_role(self):
        from django.test import RequestFactory
        from clients.admin import ClientAdmin

        request = RequestFactory().get('/')
        request.user = self.admin_user
        admin = ClientAdmin(Client, AdminSite())
        obj = Client.objects.get(pk=self.client_record.pk)
        admin.save_model(request, obj, form=None, change=True)
        obj.status = 'completed'
        obj.save()
        obj.refresh_from_db()
        self.assertEqual(obj.staff_name, 'Original Manager')

    def test_api_update_reassigns_case_manager(self):
        self.api.force_authenticate(self.case_manager)
        response = self.api.patch(
            f'/api/clients/{self.client_record.pk}/',
            {'status': 'active', 'additional_notes': 'Follow-up call'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.client_record.refresh_from_db()
        self.assertEqual(self.client_record.staff_name, 'Maria Lopez')


class ClientOutcomesReportTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create_superuser(
            username='reportadmin',
            password='testpass123',
            email='reports@example.com',
        )
        self.django_client = DjangoTestClient()
        self.django_client.force_login(self.staff)
        old = Client.objects.create(
            first_name='Old',
            last_name='Client',
            phone='4155551001',
            gender='M',
            training_interest='general',
            status='active',
        )
        old.created_at = timezone.now() - timedelta(days=400)
        old.save(update_fields=['created_at'])

    def test_outcomes_without_created_range_includes_all_clients(self):
        Client.objects.create(
            first_name='New',
            last_name='Client',
            phone='4155551002',
            gender='M',
            training_interest='general',
            status='active',
        )
        url = reverse('client-outcomes-report-csv')
        response = self.django_client.get(url)
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        rows = [line for line in body.strip().split('\n') if line]
        self.assertEqual(len(rows), Client.objects.count() + 1)

    def test_outcomes_package_zip_downloads(self):
        url = reverse('client-outcomes-package')
        response = self.django_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/zip')


class CityBuildMissingDocsReportTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create_superuser(
            username='cbreport',
            password='testpass123',
            email='cbreport@example.com',
        )
        self.django_client = DjangoTestClient()
        self.django_client.force_login(self.staff)
        self.citybuild_client = Client.objects.create(
            first_name='Build',
            last_name='Candidate',
            phone='4155552001',
            gender='M',
            training_interest='citybuild',
            status='active',
            staff_name='Maria',
        )
        Client.objects.create(
            first_name='General',
            last_name='Client',
            phone='4155552002',
            gender='M',
            training_interest='general',
            status='active',
        )
        Client.objects.create(
            first_name='Capsa',
            last_name='Only',
            phone='4155552003',
            gender='M',
            training_interest='capsa',
            status='active',
        )
        from clients.models import Document
        Document.objects.create(
            client=self.citybuild_client,
            title='TABE',
            doc_type='cb_tabe',
            file=SimpleUploadedFile('tabe.pdf', b'%PDF'),
            uploaded_by='admin',
        )

    def test_citybuild_missing_docs_csv_lists_only_citybuild_clients(self):
        url = reverse('citybuild-missing-docs-report-csv')
        response = self.django_client.get(url)
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        rows = [line for line in body.strip().split('\n') if line]
        self.assertEqual(len(rows), 2)
        self.assertIn('Build Candidate', body)
        self.assertIn('TABE', body)
        self.assertNotIn('General Client', body)
        self.assertNotIn('Capsa Only', body)

    def test_citybuild_missing_docs_incomplete_only_skips_complete_packets(self):
        from clients.citybuild_docs import CITYBUILD_CHECKLIST_ITEMS
        from clients.models import Document
        for _panel, code, _label, source in CITYBUILD_CHECKLIST_ITEMS:
            if source == 'document' and code:
                Document.objects.create(
                    client=self.citybuild_client,
                    title=code,
                    doc_type=code,
                    file=SimpleUploadedFile(f'{code}.pdf', b'%PDF'),
                    uploaded_by='admin',
                )
        self.citybuild_client.resume = SimpleUploadedFile('resume.pdf', b'%PDF')
        self.citybuild_client.save()
        from clients.models import CaseNote
        CaseNote.objects.create(
            client=self.citybuild_client,
            staff_member='Maria',
            note_type='general',
            content='Intake note',
        )
        url = reverse('citybuild-missing-docs-report-csv') + '?only_incomplete=1'
        response = self.django_client.get(url)
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        rows = [line for line in body.strip().split('\n') if line]
        self.assertEqual(len(rows), 1)


class StaffSpaApiTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create_user(
            username='case_mgr',
            password='staffpass123',
            email='cm@example.com',
            role='case_manager',
        )
        self.client_record = Client.objects.create(
            first_name='Maria',
            last_name='Lopez',
            phone='4155559090',
            gender='F',
            training_interest='general',
            status='active',
        )
        self.http = DjangoTestClient()

    def test_staff_login_and_client_search(self):
        login_resp = self.http.post(
            '/api/staff/login/',
            data={'username': 'case_mgr', 'password': 'staffpass123'},
            content_type='application/json',
        )
        self.assertEqual(login_resp.status_code, 200)

        list_resp = self.http.get('/api/staff/clients/?q=Lopez')
        self.assertEqual(list_resp.status_code, 200)
        payload = list_resp.json()
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]['full_name'], 'Maria Lopez')

    def test_staff_quick_case_note(self):
        self.http.login(username='case_mgr', password='staffpass123')
        response = self.http.post(
            f'/api/staff/clients/{self.client_record.pk}/notes/',
            data={
                'note_date': '2026-05-28',
                'note_type': 'general',
                'content': 'Visited today for intake follow-up.',
            },
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.client_record.case_notes.count(), 1)

    def test_staff_password_reset_always_acknowledges(self):
        response = self.http.post(
            '/api/staff/password-reset/',
            data={'email': 'nobody@example.com'},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('message', response.json())

    def test_client_list_filters_by_program_and_stage(self):
        Client.objects.create(
            first_name='Pit',
            last_name='Applicant',
            phone='4155551111',
            gender='M',
            training_interest='pit_stop',
            pit_stop_stage=Client.PIT_STOP_STAGE_APPLICANT,
        )
        Client.objects.create(
            first_name='Pit',
            last_name='Worker',
            phone='4155552222',
            gender='M',
            training_interest='pit_stop',
            pit_stop_stage=Client.PIT_STOP_STAGE_WORKER,
        )
        self.http.login(username='case_mgr', password='staffpass123')

        program_resp = self.http.get('/api/staff/clients/?program=pit_stop')
        self.assertEqual(program_resp.status_code, 200)
        self.assertEqual(len(program_resp.json()), 2)

        stage_resp = self.http.get('/api/staff/clients/?program=pit_stop&stage=applicant')
        self.assertEqual(stage_resp.status_code, 200)
        stage_payload = stage_resp.json()
        self.assertEqual(len(stage_payload), 1)
        self.assertEqual(stage_payload[0]['full_name'], 'Pit Applicant')

    def test_guard_card_is_a_valid_program(self):
        self.http.login(username='case_mgr', password='staffpass123')
        response = self.http.patch(
            f'/api/staff/clients/{self.client_record.pk}/',
            data={'training_interest': 'guard_card'},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()['training_interest_display'],
            'Security Guard Card Training',
        )

    def test_dashboard_surfaces_only_new_pitstop_applications(self):
        new_client = Client.objects.create(
            first_name='New',
            last_name='Candidate',
            phone='6285551212',
            gender='F',
            dob=date(1999, 4, 2),
            training_interest='pit_stop',
        )
        reviewed_client = Client.objects.create(
            first_name='Reviewed',
            last_name='Candidate',
            phone='4155551313',
            gender='M',
            dob=date(1989, 4, 2),
            training_interest='pit_stop',
        )
        PitStopApplication.objects.create(
            client=new_client,
            position_applied_for='Pit Stop Attendant',
        )
        PitStopApplication.objects.create(
            client=reviewed_client,
            position_applied_for='Pit Stop Attendant',
            review_status=PitStopApplication.REVIEW_INTERVIEWED,
        )
        self.http.login(username='case_mgr', password='staffpass123')

        response = self.http.get('/api/staff/dashboard/new-pitstop-applications/')

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['total_new'], 1)
        self.assertEqual([row['full_name'] for row in body['results']], ['New Candidate'])
        self.assertEqual(body['results'][0]['area_code'], '628')

    def test_client_detail_includes_pitstop_application_summary(self):
        self.client_record.training_interest = 'pit_stop'
        self.client_record.dob = date(1990, 6, 4)
        self.client_record.save(update_fields=['training_interest', 'dob'])
        PitStopApplication.objects.create(
            client=self.client_record,
            position_applied_for='Pit Stop Attendant',
            review_status=PitStopApplication.REVIEW_MAYBE,
            review_notes='Strong interview; check schedule.',
            weekly_schedule={'Monday': ['7-4']},
        )
        self.http.login(username='case_mgr', password='staffpass123')

        response = self.http.get(f'/api/staff/clients/{self.client_record.pk}/')

        self.assertEqual(response.status_code, 200)
        app = response.json()['pit_stop_application']
        self.assertEqual(app['review_status'], PitStopApplication.REVIEW_MAYBE)
        self.assertEqual(app['review_notes'], 'Strong interview; check schedule.')
        self.assertEqual(app['available_days'], ['Monday'])


class StaffPitStopPromoteTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create_user(
            username='pit_mgr',
            password='staffpass123',
            email='pit@example.com',
            role='case_manager',
        )
        self.client_record = Client.objects.create(
            first_name='Andre',
            last_name='Diaz',
            phone='4155553434',
            gender='M',
            training_interest='pit_stop',
            pit_stop_stage=Client.PIT_STOP_STAGE_ACTIVE_PARTICIPANT,
        )
        self.http = DjangoTestClient()
        self.url = f'/api/staff/clients/{self.client_record.pk}/pitstop/promote/'

    def test_promote_creates_worker_account_and_sets_stage(self):
        self.http.login(username='pit_mgr', password='staffpass123')
        response = self.http.post(self.url, content_type='application/json')
        self.assertEqual(response.status_code, 201)

        account = WorkerAccount.objects.get(client=self.client_record)
        self.assertEqual(account.phone, '4155553434')
        self.assertTrue(account.is_active)
        self.assertTrue(account.check_pin('3434'))

        self.client_record.refresh_from_db()
        self.assertEqual(self.client_record.pit_stop_stage, Client.PIT_STOP_STAGE_WORKER)
        self.assertTrue(response.json()['client']['worker_portal']['portal_access'])

    def test_promote_twice_is_rejected(self):
        self.http.login(username='pit_mgr', password='staffpass123')
        self.http.post(self.url, content_type='application/json')
        second = self.http.post(self.url, content_type='application/json')
        self.assertEqual(second.status_code, 400)
        self.assertEqual(WorkerAccount.objects.filter(client=self.client_record).count(), 1)

    def test_promote_without_usable_phone_fails(self):
        Client.objects.filter(pk=self.client_record.pk).update(phone='555')
        self.http.login(username='pit_mgr', password='staffpass123')
        response = self.http.post(self.url, content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('phone', response.json()['error'].lower())
        self.assertFalse(WorkerAccount.objects.filter(client=self.client_record).exists())

    def test_promote_requires_staff(self):
        User = get_user_model()
        # 'volunteer' is the one role StaffUser.save() does not promote to is_staff.
        User.objects.create_user(
            username='outsider',
            password='outsider123',
            email='outsider@example.com',
            role='volunteer',
            is_staff=False,
        )
        self.http.login(username='outsider', password='outsider123')
        response = self.http.post(self.url, content_type='application/json')
        self.assertIn(response.status_code, (401, 403))
        self.assertFalse(WorkerAccount.objects.filter(client=self.client_record).exists())


@override_settings(
    AZURE_COMMUNICATION_CONNECTION_STRING='endpoint=https://example.test/;accesskey=fake',
    AZURE_COMMUNICATION_SMS_FROM='+15555550123',
    SMS_CLASS_CONFIRMATION_ENABLED=True,
)
class ClassConfirmationSmsTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create_user(
            username='class_mgr',
            password='staffpass123',
            email='classes@example.com',
            role='case_manager',
        )
        self.client_record = Client.objects.create(
            first_name='Marco',
            last_name='Reyes',
            phone='4155557788',
            gender='M',
            training_interest='general',
        )
        self.template = ClassTemplate.objects.create(
            name='Job Readiness Training',
            category='job_readiness',
            location='3120 Mission St',
            start_time=time(9, 0),
            end_time=time(12, 0),
        )
        self.session = ClassSession.objects.create(
            template=self.template,
            session_date=timezone.localdate() + timedelta(days=7),
            start_time=time(9, 0),
            end_time=time(12, 0),
            location='3120 Mission St',
            capacity=20,
        )
        self.http = DjangoTestClient()
        self.http.login(username='class_mgr', password='staffpass123')
        self.url = f'/api/staff/classes/{self.session.pk}/enroll/'

    @staticmethod
    def _sent_result():
        class SmsResult:
            successful = True
            message_id = 'msg-class-1'
            http_status_code = 202
            error_message = None

        return [SmsResult()]

    @patch('clients.notifications._sms_client')
    def test_enrolling_texts_the_client_the_date_and_time(self, sms_client_mock):
        sms_client_mock.return_value.send.return_value = self._sent_result()

        response = self.http.post(
            self.url,
            data={'client_id': self.client_record.pk},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['text_outcome'], 'sent')

        log = ClientTextMessage.objects.get(client=self.client_record)
        self.assertEqual(log.purpose, ClientTextMessage.PURPOSE_CLASS_CONFIRMATION)
        self.assertEqual(log.status, ClientTextMessage.STATUS_SENT)
        self.assertEqual(log.to_phone, '+14155557788')
        self.assertIn('Job Readiness Training', log.body)
        self.assertIn('9:00 AM', log.body)
        self.assertIn('3120 Mission St', log.body)
        self.assertIn('Marco', log.body)

    @patch('clients.notifications._sms_client')
    def test_no_text_when_feature_is_off(self, sms_client_mock):
        with override_settings(SMS_CLASS_CONFIRMATION_ENABLED=False):
            response = self.http.post(
                self.url,
                data={'client_id': self.client_record.pk},
                content_type='application/json',
            )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['text_outcome'], 'disabled')
        sms_client_mock.assert_not_called()
        self.assertFalse(ClientTextMessage.objects.exists())

    @patch('clients.notifications._sms_client')
    def test_no_text_for_a_class_that_already_happened(self, sms_client_mock):
        past = ClassSession.objects.create(
            template=self.template,
            session_date=timezone.localdate() - timedelta(days=3),
            start_time=time(9, 0),
            end_time=time(12, 0),
            capacity=20,
        )
        response = self.http.post(
            f'/api/staff/classes/{past.pk}/enroll/',
            data={'client_id': self.client_record.pk},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['text_outcome'], 'skipped')
        sms_client_mock.assert_not_called()

    @patch('clients.notifications._sms_client')
    def test_reenrolling_does_not_text_twice(self, sms_client_mock):
        sms_client_mock.return_value.send.return_value = self._sent_result()

        self.http.post(
            self.url,
            data={'client_id': self.client_record.pk},
            content_type='application/json',
        )
        self.http.post(
            f'/api/staff/classes/{self.session.pk}/unenroll/',
            data={'client_id': self.client_record.pk},
            content_type='application/json',
        )
        again = self.http.post(
            self.url,
            data={'client_id': self.client_record.pk},
            content_type='application/json',
        )

        self.assertEqual(again.status_code, 201)
        self.assertEqual(ClientTextMessage.objects.count(), 1)
        self.assertEqual(sms_client_mock.return_value.send.call_count, 1)

    @patch('clients.notifications._sms_client')
    def test_enrollment_still_succeeds_when_sms_provider_fails(self, sms_client_mock):
        sms_client_mock.side_effect = RuntimeError('Azure unreachable')

        response = self.http.post(
            self.url,
            data={'client_id': self.client_record.pk},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['text_outcome'], 'failed')
        self.assertTrue(response.json()['text_warning'])
        self.assertTrue(
            ClassEnrollment.objects.filter(
                session=self.session, client=self.client_record, status='registered'
            ).exists()
        )

    def _preview(self, session=None, client_record=None):
        session = session or self.session
        client_record = client_record or self.client_record
        return self.http.get(
            f'/api/staff/classes/{session.pk}/text-preview/',
            data={'client_id': client_record.pk},
        )

    @patch('clients.notifications._sms_client')
    def test_preview_shows_the_message_before_staff_press_add(self, sms_client_mock):
        response = self._preview()
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body['will_send'])
        self.assertEqual(body['to_phone'], '4155557788')
        self.assertIn('Job Readiness Training', body['body'])
        self.assertIn('9:00 AM', body['body'])
        sms_client_mock.assert_not_called()
        self.assertFalse(ClientTextMessage.objects.exists())

    def test_preview_is_the_same_wording_that_gets_sent(self):
        preview_body = self._preview().json()['body']
        with patch('clients.notifications._sms_client') as sms_client_mock:
            sms_client_mock.return_value.send.return_value = self._sent_result()
            self.http.post(
                self.url,
                data={'client_id': self.client_record.pk},
                content_type='application/json',
            )
        self.assertEqual(ClientTextMessage.objects.get().body, preview_body)

    def test_preview_warns_staff_when_texting_is_turned_off(self):
        with override_settings(SMS_CLASS_CONFIRMATION_ENABLED=False):
            body = self._preview().json()
        self.assertFalse(body['will_send'])
        self.assertIn('turned off', body['reason'])

    def test_preview_warns_staff_when_there_is_no_phone_number(self):
        no_phone = Client.objects.create(first_name='Ana', last_name='Silva', phone='', gender='F')
        body = self._preview(client_record=no_phone).json()
        self.assertFalse(body['will_send'])
        self.assertIn('No phone number', body['reason'])

    def test_preview_requires_staff(self):
        anon = DjangoTestClient()
        response = anon.get(
            f'/api/staff/classes/{self.session.pk}/text-preview/',
            data={'client_id': self.client_record.pk},
        )
        self.assertIn(response.status_code, (401, 403))


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class PublicClientRegistrationTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.api = APIClient()

    def _registration_payload(self):
        return {
            'first_name': 'Public',
            'last_name': 'Applicant',
            'phone': '4155559090',
            'gender': 'M',
            'training_interest': 'capsa',
            'sf_resident': 'yes',
            'neighborhood': 'mission',
            'demographic_info': 'other',
            'language': 'en',
            'highest_degree': 'hs',
            'employment_status': 'unemployed',
            'referral_source': 'walk_in',
        }

    def test_public_registration_without_id_succeeds(self):
        response = self.api.post('/api/clients/', self._registration_payload(), format='multipart')
        self.assertEqual(response.status_code, 201)
        client = Client.objects.get(pk=response.json()['id'])
        self.assertFalse(client.documents.filter(doc_type='id').exists())

    def test_public_registration_accepts_json(self):
        """The signup form posts JSON now that it no longer uploads files."""
        response = self.api.post('/api/clients/', self._registration_payload(), format='json')
        self.assertEqual(response.status_code, 201)
        client = Client.objects.get(pk=response.json()['id'])
        self.assertEqual(client.first_name, 'Public')
        self.assertFalse(client.documents.exists())

    def test_public_registration_accepts_optional_government_id(self):
        response = self.api.post(
            '/api/clients/',
            {
                **self._registration_payload(),
                'doc_id': SimpleUploadedFile('license.jpg', b'fakejpeg', content_type='image/jpeg'),
            },
            format='multipart',
        )
        self.assertEqual(response.status_code, 201)
        client = Client.objects.get(pk=response.json()['id'])
        self.assertTrue(client.documents.filter(doc_type='id').exists())

    def test_registration_keeps_a_typed_in_area_for_someone_outside_sf(self):
        response = self.api.post(
            '/api/clients/',
            {
                **self._registration_payload(),
                'sf_resident': 'no',
                'neighborhood': 'outside_sf',
                'neighborhood_other': 'Daly City',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        client = Client.objects.get(pk=response.json()['id'])
        self.assertEqual(client.neighborhood, 'outside_sf')
        self.assertEqual(client.neighborhood_other, 'Daly City')


class PitStopApplicationReviewTests(TestCase):
    """The review pipeline that replaced the paper application stack."""

    def setUp(self):
        self.api = APIClient()
        self.client_record = Client.objects.create(
            first_name='Dana',
            last_name='Ruiz',
            phone='(628) 555-0142',
            gender='F',
            dob=date(1994, 5, 20),
            training_interest='pit_stop',
        )
        self.application = PitStopApplication.objects.create(
            client=self.client_record,
            position_applied_for='Pit Stop Attendant',
        )

    def test_a_new_application_starts_in_needs_review(self):
        self.assertEqual(self.application.review_status, PitStopApplication.REVIEW_NEW)

    def test_age_and_area_code_come_from_the_client_record(self):
        self.assertEqual(self.application.area_code, '628')
        expected_age = self.client_record.age
        self.assertEqual(self.application.applicant_age, expected_age)

    def test_area_code_handles_a_leading_country_code(self):
        self.client_record.phone = '+1 415 555 0199'
        self.client_record.save(update_fields=['phone'])
        self.application.refresh_from_db()
        self.assertEqual(self.application.area_code, '415')

    def test_age_is_blank_rather_than_wrong_without_a_birth_date(self):
        self.client_record.dob = None
        self.client_record.save(update_fields=['dob'])
        self.application.refresh_from_db()
        self.assertIsNone(self.application.applicant_age)

    def test_resume_shows_as_on_file_when_uploaded_as_a_document(self):
        self.assertFalse(self.application.has_resume)
        Document.objects.create(
            client=self.client_record,
            title='Resume',
            doc_type='resume',
            file=SimpleUploadedFile('resume.pdf', b'%PDF-1.4', content_type='application/pdf'),
            uploaded_by='staff',
        )
        self.assertTrue(self.application.has_resume)

    def test_an_applicant_cannot_set_their_own_review_status(self):
        response = self.api.post(
            '/api/pitstop-applications/',
            {
                'client': self.client_record.pk,
                'position_applied_for': 'Pit Stop Attendant',
                'review_status': PitStopApplication.REVIEW_MOVING_FORWARD,
                'review_notes': 'Please hire me',
                'reviewed_by': 'Not A Real Reviewer',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        created = PitStopApplication.objects.get(pk=response.json()['id'])
        self.assertEqual(created.review_status, PitStopApplication.REVIEW_NEW)
        self.assertEqual(created.review_notes, '')
        self.assertEqual(created.reviewed_by, '')


class PitStopApplicationAdminTests(TestCase):
    def setUp(self):
        from .admin import PitStopApplicationAdmin

        self.site = AdminSite()
        self.admin = PitStopApplicationAdmin(PitStopApplication, self.site)
        User = get_user_model()
        self.reviewer = User.objects.create_user(
            username='pitstop_reviewer',
            password='staffpass123',
            email='reviewer@example.com',
            first_name='Rosa',
            last_name='Lane',
            role='case_manager',
        )
        self.applications = []
        for first_name, phone, dob in [
            ('Young', '4155550111', date(2004, 1, 10)),
            ('Middle', '6285550122', date(1985, 1, 10)),
            ('Older', '5105550133', date(1962, 1, 10)),
        ]:
            client_record = Client.objects.create(
                first_name=first_name,
                last_name='Applicant',
                phone=phone,
                gender='M',
                dob=dob,
                training_interest='pit_stop',
            )
            self.applications.append(
                PitStopApplication.objects.create(
                    client=client_record, position_applied_for='Pit Stop Attendant'
                )
            )

    def test_bulk_action_records_the_status_and_who_decided(self):
        request = type('Req', (), {'user': self.reviewer})()
        with patch.object(self.admin, 'message_user'):
            self.admin.mark_interviewed(request, PitStopApplication.objects.all())

        for app in PitStopApplication.objects.all():
            self.assertEqual(app.review_status, PitStopApplication.REVIEW_INTERVIEWED)
            self.assertIn('Rosa', app.reviewed_by)
            self.assertIsNotNone(app.review_updated_at)

    def test_age_filter_narrows_to_one_applicant(self):
        from .admin import ApplicantAgeFilter

        filt = ApplicantAgeFilter(
            None, {'age_band': ['35_44']}, PitStopApplication, self.admin
        )
        results = filt.queryset(None, PitStopApplication.objects.all())
        self.assertEqual([a.client.first_name for a in results], ['Middle'])

    def test_area_code_filter_narrows_to_one_applicant(self):
        from .admin import ApplicantAreaCodeFilter

        filt = ApplicantAreaCodeFilter(
            None, {'area_code': ['510']}, PitStopApplication, self.admin
        )
        results = filt.queryset(None, PitStopApplication.objects.all())
        self.assertEqual([a.client.first_name for a in results], ['Older'])

    def test_resume_filter_finds_applications_still_missing_one(self):
        from .admin import ApplicantResumeFilter

        filt = ApplicantResumeFilter(None, {'resume': ['no']}, PitStopApplication, self.admin)
        results = filt.queryset(None, PitStopApplication.objects.all())
        self.assertEqual(results.count(), 3)


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class SelfServeDocumentUploadTests(TestCase):
    """The signup form attaches files after the client record exists."""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.api = APIClient()
        self.url = '/api/kiosk/check-in/upload-document/'
        self.client_record = Client.objects.create(
            first_name='Upload',
            last_name='Tester',
            phone='4155551234',
            gender='M',
        )

    def _post(self, **overrides):
        payload = {
            'client_id': self.client_record.pk,
            'phone': '4155551234',
            'doc_type': 'resume',
            'file': SimpleUploadedFile('resume.pdf', b'%PDF-1.4 fake', content_type='application/pdf'),
        }
        payload.update(overrides)
        return self.api.post(self.url, payload, format='multipart')

    def test_resume_upload_also_fills_the_client_resume_field(self):
        response = self._post()
        self.assertEqual(response.status_code, 201)
        self.client_record.refresh_from_db()
        self.assertTrue(self.client_record.documents.filter(doc_type='resume').exists())
        self.assertTrue(self.client_record.has_resume)

    def test_id_upload_still_works_without_a_doc_type(self):
        response = self._post(
            doc_type='',
            file=SimpleUploadedFile('license.jpg', b'fakejpeg', content_type='image/jpeg'),
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(self.client_record.documents.filter(doc_type='id').exists())

    def test_a_word_document_is_not_accepted_as_an_id(self):
        response = self._post(
            doc_type='id',
            file=SimpleUploadedFile('resume.docx', b'fake', content_type='application/msword'),
        )
        self.assertEqual(response.status_code, 400)

    def test_other_document_types_are_refused(self):
        response = self._post(doc_type='ssn_card')
        self.assertEqual(response.status_code, 400)

    def test_a_mismatched_phone_cannot_attach_files_to_someone_else(self):
        response = self._post(phone='4155559999')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(self.client_record.documents.exists())
