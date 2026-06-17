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
    ReportsHubView,
    AvailableWorkersCSVView,
    JobPlacementsReportCSVView,
    CallOutReportCSVView,
    TodaysAssignmentsCSVView,
    ClientOutcomesReportCSVView,
    ClientOutcomesPackageView,
    ManagerOperationsPackageView,
    StaffFollowUpScorecardCSVView,
    WorkforceInventoryPackageView,
    ClientFilePackageView,
    PitStopHoursReportCSVView,
    PitStopHoursPrintableView,
    PitStopHoursPackageView,
    CityBuildMissingDocsReportCSVView,
)
from .worker_views import (
    worker_login,
    worker_logout,
    worker_profile,
    worker_profile_update,
    worker_work_sites,
    worker_time_punch,
    worker_incident_report,
    worker_daily_feedback,
)
from .kiosk_views import KioskCheckInLookupView, KioskCheckInSubmitView, KioskDocumentUploadView
from .staff_views import (
    staff_csrf,
    staff_session,
    staff_login,
    staff_logout,
    staff_clients,
    staff_client_detail,
    staff_client_notes,
    staff_password_reset,
    staff_password_reset_confirm,
    staff_messages,
    staff_messages_unread_count,
)

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
    path('reports/', ReportsHubView.as_view(), name='reports-hub'),
    path('reports/available-workers/', AvailableWorkersCSVView.as_view(), name='available-workers-csv'),
    path('reports/job-placements/', JobPlacementsReportCSVView.as_view(), name='job-placements-report-csv'),
    path('reports/callouts/', CallOutReportCSVView.as_view(), name='callouts-report-csv'),
    path('reports/todays-assignments/', TodaysAssignmentsCSVView.as_view(), name='todays-assignments-csv'),
    path('reports/client-outcomes/', ClientOutcomesReportCSVView.as_view(), name='client-outcomes-report-csv'),
    path('reports/client-outcomes-package/', ClientOutcomesPackageView.as_view(), name='client-outcomes-package'),
    path('reports/manager-operations-package/', ManagerOperationsPackageView.as_view(), name='manager-operations-package'),
    path('reports/staff-followup-scorecard/', StaffFollowUpScorecardCSVView.as_view(), name='staff-followup-scorecard-csv'),
    path('reports/workforce-inventory-package/', WorkforceInventoryPackageView.as_view(), name='workforce-inventory-package'),
    path('reports/client-file-package/', ClientFilePackageView.as_view(), name='client-file-package'),
    path('reports/pitstop-hours/', PitStopHoursReportCSVView.as_view(), name='pitstop-hours-report-csv'),
    path('reports/pitstop-hours/print/', PitStopHoursPrintableView.as_view(), name='pitstop-hours-printable'),
    path('reports/pitstop-hours-package/', PitStopHoursPackageView.as_view(), name='pitstop-hours-package'),
    path(
        'reports/citybuild-missing-docs/',
        CityBuildMissingDocsReportCSVView.as_view(),
        name='citybuild-missing-docs-report-csv',
    ),
    
    # Worker Portal API (open shifts + cover interest)
    path('worker/login/', worker_login, name='worker-login'),
    path('worker/logout/', worker_logout, name='worker-logout'),
    path('worker/profile/', worker_profile, name='worker-profile'),
    path('worker/profile/update/', worker_profile_update, name='worker-profile-update'),
    path('worker/work-sites/', worker_work_sites, name='worker-work-sites'),
    path('worker/time-punch/', worker_time_punch, name='worker-time-punch'),
    path('worker/incident-report/', worker_incident_report, name='worker-incident-report'),
    path('worker/daily-feedback/', worker_daily_feedback, name='worker-daily-feedback'),
    # Lobby kiosk: self check-in case note (static web app -> API)
    path('kiosk/check-in/lookup/', KioskCheckInLookupView.as_view(), name='kiosk-check-in-lookup'),
    path('kiosk/check-in/submit/', KioskCheckInSubmitView.as_view(), name='kiosk-check-in-submit'),
    path('kiosk/check-in/upload-document/', KioskDocumentUploadView.as_view(), name='kiosk-check-in-upload-document'),

    # Staff SPA (Django session auth)
    path('staff/csrf/', staff_csrf, name='staff-csrf'),
    path('staff/session/', staff_session, name='staff-session'),
    path('staff/login/', staff_login, name='staff-login'),
    path('staff/logout/', staff_logout, name='staff-logout'),
    path('staff/clients/', staff_clients, name='staff-clients'),
    path('staff/clients/<int:pk>/', staff_client_detail, name='staff-client-detail'),
    path('staff/clients/<int:pk>/notes/', staff_client_notes, name='staff-client-notes'),
    path('staff/password-reset/', staff_password_reset, name='staff-password-reset'),
    path('staff/password-reset/confirm/', staff_password_reset_confirm, name='staff-password-reset-confirm'),
    path('staff/messages/', staff_messages, name='staff-messages'),
    path('staff/messages/unread-count/', staff_messages_unread_count, name='staff-messages-unread-count'),
]