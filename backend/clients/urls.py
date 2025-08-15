from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ClientViewSet, CaseNoteViewSet

router = DefaultRouter()
router.register(r'clients', ClientViewSet)
router.register(r'case-notes', CaseNoteViewSet)

urlpatterns = [
    path('', include(router.urls)),
]