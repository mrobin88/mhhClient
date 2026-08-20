from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.shortcuts import render
from urllib.parse import urlencode

def api_info(request):
    """Styled home hub for admin, APIs, and reporting."""
    return render(
        request,
        'home_hub.html',
        {
            'sections': [
                {
                    'title': 'Admin and Operations',
                    'items': [
                        {'name': 'Staff Admin', 'path': '/admin/', 'description': 'Manage clients, workers, staffing, and documents.'},
                        {'name': 'Staff SPA', 'path': settings.STAFF_APP_BASE_URL, 'description': 'Mobile-friendly staff workspace (same login as admin).'},
                        {'name': 'How everything works', 'path': f'{settings.STAFF_APP_BASE_URL}/#/how-it-works', 'description': 'Single guide to every app, the client path, and what runs automatically.'},
                        {'name': 'Reports Hub', 'path': '/api/reports/', 'description': 'Download filtered CSV and ZIP exports.'},
                        {'name': 'Health Check', 'path': '/health', 'description': 'Service heartbeat for platform monitoring.'},
                    ],
                },
                {
                    'title': 'Core APIs',
                    'items': [
                        {'name': 'API Root', 'path': '/api/', 'description': 'Browsable root for all API endpoints.'},
                        {'name': 'Clients API', 'path': '/api/clients/', 'description': 'Client records and workflow data.'},
                        {'name': 'PitStop Applications', 'path': '/api/pitstop-applications/', 'description': 'PitStop application intake endpoints.'},
                        {'name': 'Partner referrals (POST)', 'path': '/api/partners/v1/referrals/', 'description': 'Write-only partner ingest (API key).'},
                    ],
                },
                {
                    'title': 'Partners',
                    'items': [
                        {'name': 'Partner API docs', 'path': f'{settings.PUBLIC_APP_BASE_URL}/partners/', 'description': 'Technical docs for write-only partner referral ingest.'},
                        {'name': 'Partners in Admin', 'path': '/admin/clients/partner/', 'description': 'Create partners, rotate keys, review referrals.'},
                    ],
                },
                {
                    'title': 'Kiosk and Worker Flow',
                    'items': [
                        {'name': 'Kiosk Lookup (POST)', 'path': '/api/kiosk/check-in/lookup/', 'description': 'Lobby check-in lookup endpoint.'},
                        {'name': 'Kiosk Submit (POST)', 'path': '/api/kiosk/check-in/submit/', 'description': 'Lobby check-in submission endpoint.'},
                        {'name': 'Worker Login API (POST)', 'path': '/api/worker/login/', 'description': 'Worker portal session login endpoint.'},
                    ],
                },
            ],
        },
    )

def health_check(request):
    """
    Health check endpoint for Azure App Service Health Check feature.
    Returns a 200 status code if the application is running.
    """
    return JsonResponse({
        'status': 'healthy',
        'service': 'mhh-client-backend'
    }, status=200)


def permission_denied(request, exception=None):
    query = urlencode({
        'create': '1',
        'title': 'Admin access request',
        'description': f'I need access to this admin page: {request.path}',
        'tags': 'auth',
    })
    return render(
        request,
        '403.html',
        {
            'ticket_url': f"{settings.STAFF_APP_BASE_URL}/#/tickets?{query}",
            'support_email': getattr(settings, 'SUPPORT_EMAIL', settings.DEFAULT_FROM_EMAIL),
        },
        status=403,
    )


handler403 = permission_denied

urlpatterns = [
    path(
        'admin/password_reset/',
        auth_views.PasswordResetView.as_view(),
        name='admin_password_reset',
    ),
    path(
        'admin/password_reset/done/',
        auth_views.PasswordResetDoneView.as_view(),
        name='password_reset_done',
    ),
    path(
        'reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(),
        name='password_reset_confirm',
    ),
    path(
        'reset/done/',
        auth_views.PasswordResetCompleteView.as_view(),
        name='password_reset_complete',
    ),
    path('admin/', admin.site.urls),
    path('api/', include('clients.urls')),  # This delegates /api/ URLs to clients app
    path('health', health_check, name='health'),  # Health check endpoint for Azure
    path('', api_info, name='home'),  # Root URL shows API info
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
