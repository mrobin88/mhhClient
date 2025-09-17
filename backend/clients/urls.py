from django.urls import path, include
from rest_framework.routers import DefaultRouter
<<<<<<< HEAD
from .views import ClientViewSet, CaseNoteViewSet, DocumentDownloadView, client_dashboard_stats, PitStopApplicationViewSet
=======
from .views import ClientViewSet, CaseNoteViewSet, PitStopApplicationViewSet
>>>>>>> 92acc44 (Pit Stop Program: backend model/serializer/viewset/routes + client fields; frontend ClientForm Pit Stop section + StaffDashboard PDF; add run-local-azure.sh; add migration)

router = DefaultRouter()
router.register(r'clients', ClientViewSet)
router.register(r'case-notes', CaseNoteViewSet)
router.register(r'pitstop-applications', PitStopApplicationViewSet, basename='pitstop-application')

urlpatterns = [
    path('', include(router.urls)),
    path('documents/<int:pk>/download/', DocumentDownloadView.as_view(), name='document-download'),
    path('dashboard/stats/', client_dashboard_stats, name='client-dashboard-stats'),
]