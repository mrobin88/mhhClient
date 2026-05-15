import shutil
import tempfile
from datetime import date, time

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from clients.models import Client
from clients.models_extensions import WorkerAccount, WorkerShiftProof, WorkAssignment, WorkSite
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
