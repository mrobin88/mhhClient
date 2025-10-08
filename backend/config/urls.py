from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.http import HttpResponse

def home_redirect(request):
    """Redirect to frontend application"""
    # Update this URL to your actual frontend URL
    return redirect('https://your-frontend-domain.com')

def api_info(request):
    """Simple API info page"""
    return HttpResponse("""
    <h1>Client Services API</h1>
    <p>Available endpoints:</p>
    <ul>
        <li><a href="/admin/">/admin/</a> - Django Admin</li>
        <li><a href="/api/">/api/</a> - REST API</li>
        <li><a href="/api/clients/">/api/clients/</a> - Client Management</li>
        <li><a href="/api/pitstop-applications/">/api/pitstop-applications/</a> - Applications</li>
    </ul>
    """)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('clients.urls')),  # This delegates /api/ URLs to clients app
    path('', api_info, name='home'),  # Root URL shows API info
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
