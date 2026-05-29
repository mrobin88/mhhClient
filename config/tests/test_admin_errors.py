from django.contrib.auth import get_user_model
from django.test import Client as DjangoTestClient, TestCase, override_settings


@override_settings(ADMIN_SHOW_EXCEPTION_DETAILS=True)
class AdminExceptionDiagnosticsTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.superuser = User.objects.create_superuser(
            username='diag_admin',
            password='testpass123',
            email='diag@example.com',
        )
        self.client = DjangoTestClient()
        self.client.force_login(self.superuser)

    def test_superuser_sees_exception_detail_on_admin_500(self):
        from django.urls import path

        def boom(_request):
            raise ValueError('diagnostic test boom')

        from config import urls as project_urls

        project_urls.urlpatterns.insert(0, path('admin/test-boom/', boom))
        try:
            response = self.client.get('/admin/test-boom/')
            self.assertEqual(response.status_code, 500)
            self.assertContains(response, 'ValueError', status_code=500)
            self.assertContains(response, 'diagnostic test boom', status_code=500)
            self.assertContains(response, 'Traceback', status_code=500)
        finally:
            project_urls.urlpatterns.pop(0)
