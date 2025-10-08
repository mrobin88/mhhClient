from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from clients.storage import generate_document_sas_url

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

# Secure media redirect for private Azure Blob Storage
@login_required
def secure_media_redirect(request, path):
    try:
        sas_url = generate_document_sas_url(path, expiry_minutes=15)
        return redirect(sas_url)
    except Exception:
        return HttpResponse("File not found or access denied", status=404)

# Always route /media/* through secure redirect in production
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', secure_media_redirect, name='secure-media')
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
