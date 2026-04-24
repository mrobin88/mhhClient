from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ClientViewSet,
    CaseNoteViewSet,
    DocumentDownloadView,
    ResumeDownloadView,
    client_dashboard_stats,
    PitStopApplicationViewSet,
    JobPlacementViewSet,
)
from .reports import (
    AvailableWorkersCSVView,
    JobPlacementsReportCSVView,
    CallOutReportCSVView,
    TodaysAssignmentsCSVView,
    ClientOutcomesReportCSVView,
    StaffFollowUpScorecardCSVView,
    WorkforceInventoryPackageView,
)
from .worker_views import (
    worker_login,
    worker_logout,
    worker_profile,
    worker_open_shifts,
    worker_shift_interests,
    staff_shift_interest_update,
)
from .kiosk_views import KioskCheckInLookupView, KioskCheckInSubmitView, KioskDocumentUploadView

router = DefaultRouter()
router.register(r'clients', ClientViewSet)
router.register(r'case-notes', CaseNoteViewSet)
router.register(r'pitstop-applications', PitStopApplicationViewSet, basename='pitstop-application')
router.register(r'job-placements', JobPlacementViewSet, basename='job-placement')

urlpatterns = [
    path('', include(router.urls)),
    path('documents/<int:pk>/download/', DocumentDownloadView.as_view(), name='document-download'),
    path('clients/<int:pk>/resume/', ResumeDownloadView.as_view(), name='client-resume-download'),
    path('dashboard/stats/', client_dashboard_stats, name='client-dashboard-stats'),
    
    # CSV Export Reports
    path('reports/available-workers/', AvailableWorkersCSVView.as_view(), name='available-workers-csv'),
    path('reports/job-placements/', JobPlacementsReportCSVView.as_view(), name='job-placements-report-csv'),
    path('reports/callouts/', CallOutReportCSVView.as_view(), name='callouts-report-csv'),
    path('reports/todays-assignments/', TodaysAssignmentsCSVView.as_view(), name='todays-assignments-csv'),
    path('reports/client-outcomes/', ClientOutcomesReportCSVView.as_view(), name='client-outcomes-report-csv'),
    path('reports/staff-followup-scorecard/', StaffFollowUpScorecardCSVView.as_view(), name='staff-followup-scorecard-csv'),
    path('reports/workforce-inventory-package/', WorkforceInventoryPackageView.as_view(), name='workforce-inventory-package'),
    
    # Worker Portal API (open shifts + cover interest)
    path('worker/login/', worker_login, name='worker-login'),
    path('worker/logout/', worker_logout, name='worker-logout'),
    path('worker/profile/', worker_profile, name='worker-profile'),
    path('worker/open-shifts/', worker_open_shifts, name='worker-open-shifts'),
    path('worker/shift-interests/', worker_shift_interests, name='worker-shift-interests'),
    path(
        'staff/shift-interests/<int:pk>/',
        staff_shift_interest_update,
        name='staff-shift-interest-update',
    ),
    # Lobby kiosk: self check-in case note (static web app -> API)
    path('kiosk/check-in/lookup/', KioskCheckInLookupView.as_view(), name='kiosk-check-in-lookup'),
    path('kiosk/check-in/submit/', KioskCheckInSubmitView.as_view(), name='kiosk-check-in-submit'),
    path('kiosk/check-in/upload-document/', KioskDocumentUploadView.as_view(), name='kiosk-check-in-upload-document'),
]