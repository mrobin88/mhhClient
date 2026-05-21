from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render

def home_redirect(request):
    """Redirect to frontend application"""
    # Update this URL to your actual frontend URL
    return redirect('https://your-frontend-domain.com')

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

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('clients.urls')),  # This delegates /api/ URLs to clients app
    path('health', health_check, name='health'),  # Health check endpoint for Azure
    path('', api_info, name='home'),  # Root URL shows API info
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
