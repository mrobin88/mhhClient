from unittest.mock import patch

from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory, TestCase, override_settings

from users.admin import StaffUserAdmin
from users.models import StaffUser


class StaffUserAdminTests(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.admin = StaffUserAdmin(StaffUser, self.site)
        self.request = RequestFactory().get('/admin/users/staffuser/')
        self.request.user = StaffUser.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='testpass123',
        )

    def test_delete_permission_is_disabled(self):
        self.assertFalse(self.admin.has_delete_permission(self.request))
        self.assertNotIn('delete_selected', self.admin.get_actions(self.request))

    def test_delete_model_deactivates_without_removing_staff_user(self):
        staff_user = StaffUser.objects.create_user(
            username='caseworker',
            password='testpass123',
            role='case_manager',
        )

        self.admin.delete_model(self.request, staff_user)

        staff_user.refresh_from_db()
        self.assertFalse(staff_user.is_active)
        self.assertTrue(StaffUser.objects.filter(pk=staff_user.pk).exists())

    def test_delete_queryset_deactivates_without_removing_staff_users(self):
        staff_user = StaffUser.objects.create_user(
            username='counselor',
            password='testpass123',
            role='counselor',
        )

        self.admin.delete_queryset(
            self.request,
            StaffUser.objects.filter(pk=staff_user.pk),
        )

        staff_user.refresh_from_db()
        self.assertFalse(staff_user.is_active)
        self.assertTrue(StaffUser.objects.filter(pk=staff_user.pk).exists())

    def test_disable_login_action_leaves_current_user_active(self):
        staff_user = StaffUser.objects.create_user(
            username='volunteer',
            password='testpass123',
            role='volunteer',
        )

        with patch.object(self.admin, 'message_user'):
            self.admin.disable_staff_login(
                self.request,
                StaffUser.objects.filter(pk__in=[self.request.user.pk, staff_user.pk]),
            )

        staff_user.refresh_from_db()
        self.request.user.refresh_from_db()
        self.assertFalse(staff_user.is_active)
        self.assertTrue(self.request.user.is_active)

    @override_settings(
        AZURE_COMMUNICATION_CONNECTION_STRING='endpoint=https://example.test/;accesskey=fake',
        AZURE_COMMUNICATION_SMS_FROM='+15555550123',
        SMS_FORCE_EMAIL_BACKUP=True,
    )
    @patch('clients.notifications.send_phone_text_message')
    @patch('users.admin.send_mail')
    def test_text_staff_login_help_action_sends_sms_for_users_with_phone(self, send_mail_mock, send_sms_mock):
        send_sms_mock.return_value = (True, '+19255501234')
        send_mail_mock.return_value = 1
        staff_user = StaffUser.objects.create_user(
            username='caseworker',
            email='caseworker@example.com',
            password='testpass123',
            role='case_manager',
            phone='9255501234',
        )

        with patch.object(self.admin, 'message_user'):
            self.admin.text_staff_login_help(
                self.request,
                StaffUser.objects.filter(pk=staff_user.pk),
            )

        send_sms_mock.assert_called_once()
        kwargs = send_sms_mock.call_args.kwargs
        self.assertEqual(kwargs['phone'], '9255501234')
        self.assertIn('Username: caseworker', kwargs['body'])
        send_mail_mock.assert_called_once()
