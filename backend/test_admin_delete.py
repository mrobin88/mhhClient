#!/usr/bin/env python
"""
Test script to verify admin delete functionality works properly
"""
import os

# Setup Django before importing Django models
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.simple_settings')
import django
django.setup()

from django.test import TestCase, Client
from django.urls import reverse

from clients.models import Client, CaseNote, Document
from users.models import StaffUser

class AdminDeleteTestCase(TestCase):
    """Test that admin delete functionality works without 500 errors"""

    def setUp(self):
        """Create test user and client"""
        # Create superuser for admin access
        self.admin_user = StaffUser.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='testpass123'
        )

        # Create test client
        self.test_client = Client.objects.create(
            first_name='Test',
            last_name='User',
            dob='1990-01-01',
            phone='555-1234',
            email='test@example.com',
            gender='M',
            sf_resident='yes',
            neighborhood='mission',
            demographic_info='white',
            language='en',
            highest_degree='hs',
            employment_status='unemployed',
            training_interest='general',
            referral_source='other',
            status='active'
        )

        # Create related objects
        self.case_note = CaseNote.objects.create(
            client=self.test_client,
            staff_member='Test Staff',
            note_type='general',
            content='Test case note'
        )

        self.document = Document.objects.create(
            client=self.test_client,
            title='Test Document',
            doc_type='other',
            file=None,  # No actual file for test
            uploaded_by='Test Staff'
        )

    def test_admin_delete_client(self):
        """Test that deleting a client with related objects works"""
        # Login as admin
        client = Client()
        client.login(username='admin', password='testpass123')

        # Get the delete URL
        delete_url = reverse('admin:clients_client_delete', args=[self.test_client.id])

        # Make the delete request
        response = client.post(delete_url, {'post': 'yes'})

        # Should redirect (302) to admin index, not return 500
        self.assertEqual(response.status_code, 302)

        # Check that the redirect location is the admin index
        expected_location = '/admin/'
        self.assertTrue(response['Location'].endswith(expected_location))

        # Verify the client is actually deleted
        with self.assertRaises(Client.DoesNotExist):
            Client.objects.get(id=self.test_client.id)

        # Related objects should also be deleted due to CASCADE
        self.assertEqual(CaseNote.objects.filter(client=self.test_client).count(), 0)
        self.assertEqual(Document.objects.filter(client=self.test_client).count(), 0)

        print("✓ Admin delete test passed - client and related objects deleted successfully")

    def test_admin_delete_document(self):
        """Test that deleting a document works"""
        # Login as admin
        client = Client()
        client.login(username='admin', password='testpass123')

        # Get the delete URL for document
        delete_url = reverse('admin:clients_document_delete', args=[self.document.id])

        # Make the delete request
        response = client.post(delete_url, {'post': 'yes'})

        # Should redirect (302) to admin index, not return 500
        self.assertEqual(response.status_code, 302)

        # Check that the redirect location is the admin index
        expected_location = '/admin/'
        self.assertTrue(response['Location'].endswith(expected_location))

        # Verify the document is actually deleted
        with self.assertRaises(Document.DoesNotExist):
            Document.objects.get(id=self.document.id)

        print("✓ Admin delete document test passed")

if __name__ == '__main__':
    import sys

    # Create test database
    from django.core.management import execute_from_command_line
    execute_from_command_line(['manage.py', 'migrate', '--run-syncdb'])

    # Run the test
    test = AdminDeleteTestCase()
    test.setUp()

    try:
        test.test_admin_delete_client()
        test.test_admin_delete_document()
        print("\n🎉 All admin delete tests passed!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
