"""
CSV Export views and report generation for worker dispatch
"""
import csv
from datetime import date, datetime, timedelta
from django.http import HttpResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Count

from .models import Client
from .models_extensions import WorkAssignment, WorkSite


class AvailableWorkersCSVView(LoginRequiredMixin, View):
    """
    Export CSV of clients available for work assignments
    GET parameters:
        - day: specific day (monday, tuesday, etc.)
        - date: specific date (YYYY-MM-DD)
    """
    
    def get(self, request):
        # Get filters from query params
        specific_day = request.GET.get('day')  # e.g., 'monday'
        specific_date = request.GET.get('date')  # e.g., '2025-10-15'
        
        # Base queryset - active clients who have completed program
        clients = Client.objects.filter(
            status__in=['active', 'program_complete'],
            job_placed=False  # Not yet placed in permanent job
        ).select_related().prefetch_related('work_assignments')

        # `day` filter was tied to removed weekly-availability records; ignored for compatibility.
        if specific_day:
            pass
        
        # Exclude clients already assigned for specific date
        if specific_date:
            assigned_client_ids = WorkAssignment.objects.filter(
                assignment_date=specific_date,
                status__in=['confirmed', 'pending', 'in_progress']
            ).values_list('client_id', flat=True)
            clients = clients.exclude(id__in=assigned_client_ids)
        
        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        filename = f'available_workers_{date.today()}'
        if specific_day:
            filename += f'_{specific_day}'
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        
        writer = csv.writer(response)
        
        # Header row
        writer.writerow([
            'Name',
            'Phone',
            'Email',
            'Languages',
            'Available Days',
            'Recent Assignments',
            'No Shows (Last 30 days)',
            'Call Outs (Last 30 days)',
            'Status',
            'Notes'
        ])
        
        # Data rows
        for client in clients:
            available_days = ''
            
            # Count recent assignments
            thirty_days_ago = date.today() - timedelta(days=30)
            recent_assignments = client.work_assignments.filter(
                assignment_date__gte=thirty_days_ago
            ).count()
            
            # Count no-shows
            no_shows = client.work_assignments.filter(
                assignment_date__gte=thirty_days_ago,
                status='no_show'
            ).count()
            
            # Count call-outs
            call_outs = client.work_assignments.filter(
                assignment_date__gte=thirty_days_ago,
                status='called_out'
            ).count()
            
            writer.writerow([
                client.full_name,
                client.phone or '',
                client.email or '',
                client.get_language_display(),
                available_days or '—',
                recent_assignments,
                no_shows,
                call_outs,
                client.get_status_display(),
                client.additional_notes or ''
            ])
        
        return response


class WorkAssignmentsReportCSVView(LoginRequiredMixin, View):
    """
    Export CSV of work assignments for a date range
    GET parameters:
        - start_date: start date (YYYY-MM-DD)
        - end_date: end date (YYYY-MM-DD)
        - site_id: filter by work site
        - status: filter by status
    """
    
    def get(self, request):
        start_date = request.GET.get('start_date', date.today().isoformat())
        end_date = request.GET.get('end_date', (date.today() + timedelta(days=7)).isoformat())
        site_id = request.GET.get('site_id')
        status = request.GET.get('status')
        
        # Build queryset
        assignments = WorkAssignment.objects.filter(
            assignment_date__gte=start_date,
            assignment_date__lte=end_date
        ).select_related('client', 'work_site', 'replacement_client')
        
        if site_id:
            assignments = assignments.filter(work_site_id=site_id)
        
        if status:
            assignments = assignments.filter(status=status)
        
        # Create CSV
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="assignments_{start_date}_to_{end_date}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Date',
            'Worker Name',
            'Phone',
            'Work Site',
            'Start Time',
            'End Time',
            'Status',
            'Confirmed',
            'Hours Worked',
            'Assigned By',
            'Call Out Reason',
            'Replacement',
            'Notes'
        ])
        
        for assignment in assignments:
            writer.writerow([
                assignment.assignment_date,
                assignment.client.full_name,
                assignment.client.phone or '',
                assignment.work_site.name,
                assignment.start_time.strftime('%I:%M %p'),
                assignment.end_time.strftime('%I:%M %p'),
                assignment.get_status_display(),
                'Yes' if assignment.confirmed_by_client else 'No',
                assignment.hours_worked or '',
                assignment.assigned_by,
                assignment.callout_reason or '',
                assignment.replacement_client.full_name if assignment.replacement_client else '',
                assignment.assignment_notes or ''
            ])
        
        return response


class CallOutReportCSVView(LoginRequiredMixin, View):
    """
    Export CSV of assignments marked called out (manual call-outs tracked on the assignment).
    GET parameters:
        - start_date: start date (YYYY-MM-DD)
        - end_date: end date (YYYY-MM-DD)
    """

    def get(self, request):
        start_date = request.GET.get('start_date', (date.today() - timedelta(days=30)).isoformat())
        end_date = request.GET.get('end_date', date.today().isoformat())

        assignments = WorkAssignment.objects.filter(
            assignment_date__gte=start_date,
            assignment_date__lte=end_date,
            status='called_out',
        ).select_related('client', 'work_site', 'replacement_client')

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="callouts_{start_date}_to_{end_date}.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Date',
            'Worker Name',
            'Phone',
            'Work Site',
            'Called out recorded at',
            'Call-out reason',
            'Replacement found',
            'Replacement name',
            'Assignment notes',
        ])

        for a in assignments:
            writer.writerow([
                a.assignment_date,
                a.client.full_name,
                a.client.phone or '',
                a.work_site.name,
                a.called_out_at.strftime('%Y-%m-%d %I:%M %p') if a.called_out_at else '',
                a.callout_reason or '',
                'Yes' if a.replacement_found else 'No',
                a.replacement_client.full_name if a.replacement_client else '',
                a.assignment_notes or '',
            ])

        return response


class TodaysAssignmentsCSVView(LoginRequiredMixin, View):
    """Quick export of today's work assignments"""
    
    def get(self, request):
        today = date.today()
        assignments = WorkAssignment.objects.filter(
            assignment_date=today,
            status__in=['confirmed', 'in_progress']
        ).select_related('client', 'work_site').order_by('work_site__name', 'start_time')
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="todays_assignments_{today}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Work Site',
            'Worker Name',
            'Phone',
            'Start Time',
            'End Time',
            'Status',
            'Site Supervisor',
            'Supervisor Phone',
            'Notes'
        ])
        
        for assignment in assignments:
            writer.writerow([
                assignment.work_site.name,
                assignment.client.full_name,
                assignment.client.phone or '',
                assignment.start_time.strftime('%I:%M %p'),
                assignment.end_time.strftime('%I:%M %p'),
                assignment.get_status_display(),
                assignment.work_site.supervisor_name or '',
                assignment.work_site.supervisor_phone or '',
                assignment.assignment_notes or ''
            ])
        
        return response

