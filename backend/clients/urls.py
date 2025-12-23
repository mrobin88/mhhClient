from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ClientViewSet, CaseNoteViewSet, DocumentDownloadView, client_dashboard_stats, PitStopApplicationViewSet
from .reports import (
    AvailableWorkersCSVView,
    WorkAssignmentsReportCSVView,
    CallOutReportCSVView,
    TodaysAssignmentsCSVView
)

router = DefaultRouter()
router.register(r'clients', ClientViewSet)
router.register(r'case-notes', CaseNoteViewSet)
router.register(r'pitstop-applications', PitStopApplicationViewSet, basename='pitstop-application')

urlpatterns = [
    path('', include(router.urls)),
    path('documents/<int:pk>/download/', DocumentDownloadView.as_view(), name='document-download'),
    path('dashboard/stats/', client_dashboard_stats, name='client-dashboard-stats'),
    
    # CSV Export Reports
    path('reports/available-workers/', AvailableWorkersCSVView.as_view(), name='available-workers-csv'),
    path('reports/assignments/', WorkAssignmentsReportCSVView.as_view(), name='assignments-report-csv'),
    path('reports/callouts/', CallOutReportCSVView.as_view(), name='callouts-report-csv'),
    path('reports/todays-assignments/', TodaysAssignmentsCSVView.as_view(), name='todays-assignments-csv'),
]