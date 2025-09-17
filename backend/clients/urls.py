from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ClientViewSet, CaseNoteViewSet, DocumentDownloadView, client_dashboard_stats, PitStopApplicationViewSet

router = DefaultRouter()
router.register(r'clients', ClientViewSet)
router.register(r'case-notes', CaseNoteViewSet)
router.register(r'pitstop-applications', PitStopApplicationViewSet, basename='pitstop-application')

urlpatterns = [
    path('', include(router.urls)),
    path('documents/<int:pk>/download/', DocumentDownloadView.as_view(), name='document-download'),
    path('dashboard/stats/', client_dashboard_stats, name='client-dashboard-stats'),
]