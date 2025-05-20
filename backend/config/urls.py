from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('clients.urls')),  # This delegates /api/ URLs to clients app
]
