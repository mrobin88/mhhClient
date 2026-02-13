from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ClientViewSet, CaseNoteViewSet, DocumentDownloadView, ResumeDownloadView, client_dashboard_stats, PitStopApplicationViewSet
from .reports import (
    AvailableWorkersCSVView,
    WorkAssignmentsReportCSVView,
    CallOutReportCSVView,
    TodaysAssignmentsCSVView
)
from .worker_views import (
    worker_login, worker_logout, worker_profile,
    worker_assignments, worker_confirm_assignment, worker_call_out,
    worker_availability, worker_service_requests, worker_work_sites,
    worker_dashboard
)

router = DefaultRouter()
router.register(r'clients', ClientViewSet)
router.register(r'case-notes', CaseNoteViewSet)
router.register(r'pitstop-applications', PitStopApplicationViewSet, basename='pitstop-application')

urlpatterns = [
    path('', include(router.urls)),
    path('documents/<int:pk>/download/', DocumentDownloadView.as_view(), name='document-download'),
    path('clients/<int:pk>/resume/', ResumeDownloadView.as_view(), name='client-resume-download'),
    path('dashboard/stats/', client_dashboard_stats, name='client-dashboard-stats'),
    
    # CSV Export Reports
    path('reports/available-workers/', AvailableWorkersCSVView.as_view(), name='available-workers-csv'),
    path('reports/assignments/', WorkAssignmentsReportCSVView.as_view(), name='assignments-report-csv'),
    path('reports/callouts/', CallOutReportCSVView.as_view(), name='callouts-report-csv'),
    path('reports/todays-assignments/', TodaysAssignmentsCSVView.as_view(), name='todays-assignments-csv'),
    
    # Worker Portal API Endpoints
    path('worker/login/', worker_login, name='worker-login'),
    path('worker/logout/', worker_logout, name='worker-logout'),
    path('worker/profile/', worker_profile, name='worker-profile'),
    path('worker/dashboard/', worker_dashboard, name='worker-dashboard'),
    path('worker/assignments/', worker_assignments, name='worker-assignments'),
    path('worker/assignments/<int:assignment_id>/confirm/', worker_confirm_assignment, name='worker-confirm-assignment'),
    path('worker/call-out/', worker_call_out, name='worker-call-out'),
    path('worker/availability/', worker_availability, name='worker-availability'),
    path('worker/service-requests/', worker_service_requests, name='worker-service-requests'),
    path('worker/work-sites/', worker_work_sites, name='worker-work-sites'),
]