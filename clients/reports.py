"""
CSV Export views and report generation for worker dispatch
"""
import csv
from datetime import date, datetime, timedelta
from django.http import HttpResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Count

from .models import Client, CaseNote
from .models_extensions import WorkAssignment, WorkSite
from .notifications import followup_stage


def _staff_aliases(user):
    full_name = (user.get_full_name() or '').strip()
    aliases = {user.username}
    if full_name:
        aliases.add(full_name)
    if user.email:
        aliases.add(user.email)
    return aliases


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
        assigned_by = request.GET.get('assigned_by')
        mine = request.GET.get('mine')
        
        # Build queryset
        assignments = WorkAssignment.objects.filter(
            assignment_date__gte=start_date,
            assignment_date__lte=end_date
        ).select_related('client', 'work_site', 'replacement_client')
        
        if site_id:
            assignments = assignments.filter(work_site_id=site_id)
        
        if status:
            assignments = assignments.filter(status=status)

        if mine in {'1', 'true', 'True'}:
            assignments = assignments.filter(assigned_by__in=_staff_aliases(request.user))
        elif assigned_by:
            assignments = assignments.filter(assigned_by__icontains=assigned_by.strip())
        
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


class ClientOutcomesReportCSVView(LoginRequiredMixin, View):
    """
    Export client-level outcomes report for OEWD/state reporting.
    GET parameters:
      - case_manager
      - program
      - demographic
      - status
      - mine=1 (limit to current logged-in staff aliases)
    """

    def get(self, request):
        case_manager = (request.GET.get('case_manager') or '').strip()
        program = (request.GET.get('program') or '').strip()
        demographic = (request.GET.get('demographic') or '').strip()
        client_status = (request.GET.get('status') or '').strip()
        mine = request.GET.get('mine')

        clients = Client.objects.all().order_by('-created_at')
        if mine in {'1', 'true', 'True'}:
            clients = clients.filter(staff_name__in=_staff_aliases(request.user))
        elif case_manager:
            clients = clients.filter(staff_name__icontains=case_manager)
        if program:
            clients = clients.filter(training_interest=program)
        if demographic:
            clients = clients.filter(demographic_info=demographic)
        if client_status:
            clients = clients.filter(status=client_status)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = (
            f'attachment; filename="client_outcomes_{date.today().isoformat()}.csv"'
        )
        writer = csv.writer(response)
        writer.writerow([
            'Client ID',
            'Client Name',
            'Case Manager',
            'Program',
            'Demographic Group',
            'Language',
            'Employment Status',
            'Client Status',
            'Program Start',
            'Program Completed',
            'Job Placed',
            'Job Placement Date',
            'Total Case Notes',
            'Last Case Note At',
            'Follow-up Overdue Bucket',
        ])

        today = date.today()
        notes_by_client = {
            c.id: list(c.casenotes.all().order_by('-created_at'))
            for c in clients.prefetch_related('casenotes')
        }

        for client in clients:
            notes = notes_by_client.get(client.id, [])
            last_note = notes[0] if notes else None
            overdue_bucket = 'no_followup'
            for note in notes:
                stage = followup_stage(note.follow_up_date, today=today)
                # Keep worst-stage bucket encountered
                rank = {
                    'no_followup': 0,
                    'current': 1,
                    'overdue_under_30': 2,
                    'overdue_30_plus': 3,
                    'overdue_60_plus': 4,
                    'overdue_90_plus': 5,
                }
                if rank.get(stage, 0) > rank.get(overdue_bucket, 0):
                    overdue_bucket = stage

            writer.writerow([
                client.id,
                client.full_name,
                client.staff_name or '',
                client.get_training_interest_display(),
                client.get_demographic_info_display(),
                client.get_language_display(),
                client.get_employment_status_display(),
                client.get_status_display(),
                client.program_start_date.isoformat() if client.program_start_date else '',
                client.program_completed_date.isoformat() if client.program_completed_date else '',
                'Yes' if client.job_placed else 'No',
                client.job_placement_date.isoformat() if client.job_placement_date else '',
                len(notes),
                last_note.created_at.strftime('%Y-%m-%d %H:%M:%S') if last_note else '',
                overdue_bucket,
            ])

        return response


class StaffFollowUpScorecardCSVView(LoginRequiredMixin, View):
    """
    Staff performance scorecard for follow-up activity.
    Uses existing case notes (no schema changes required).
    """

    def get(self, request):
        mine = request.GET.get('mine')
        since_days = int(request.GET.get('since_days', '90') or 90)
        since_date = date.today() - timedelta(days=since_days)

        notes = CaseNote.objects.filter(created_at__date__gte=since_date).select_related('client')
        if mine in {'1', 'true', 'True'}:
            notes = notes.filter(staff_member__in=_staff_aliases(request.user))

        # Aggregate by staff_member
        scorecard = {}
        for note in notes:
            key = (note.staff_member or 'Unassigned').strip() or 'Unassigned'
            if key not in scorecard:
                scorecard[key] = {
                    'total_notes': 0,
                    'follow_up_notes': 0,
                    'clients_touched': set(),
                    'overdue_30_plus': 0,
                    'overdue_60_plus': 0,
                    'overdue_90_plus': 0,
                }
            row = scorecard[key]
            row['total_notes'] += 1
            if note.note_type == 'follow_up':
                row['follow_up_notes'] += 1
            row['clients_touched'].add(note.client_id)
            stage = followup_stage(note.follow_up_date)
            if stage == 'overdue_30_plus':
                row['overdue_30_plus'] += 1
            elif stage == 'overdue_60_plus':
                row['overdue_60_plus'] += 1
            elif stage == 'overdue_90_plus':
                row['overdue_90_plus'] += 1

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = (
            f'attachment; filename="staff_followup_scorecard_{date.today().isoformat()}.csv"'
        )
        writer = csv.writer(response)
        writer.writerow([
            'Staff Member',
            'Total Notes',
            'Follow-up Notes',
            'Clients Touched',
            'Overdue 30+',
            'Overdue 60+',
            'Overdue 90+',
            'Credits',
            'Mark',
        ])

        for staff_member, row in sorted(scorecard.items(), key=lambda item: item[0].lower()):
            credits = (
                (row['follow_up_notes'] * 3)
                + (row['total_notes'])
                - (row['overdue_30_plus'] * 2)
                - (row['overdue_60_plus'] * 3)
                - (row['overdue_90_plus'] * 4)
            )
            if credits >= 80:
                mark = 'A'
            elif credits >= 50:
                mark = 'B'
            elif credits >= 20:
                mark = 'C'
            else:
                mark = 'Needs Attention'

            writer.writerow([
                staff_member,
                row['total_notes'],
                row['follow_up_notes'],
                len(row['clients_touched']),
                row['overdue_30_plus'],
                row['overdue_60_plus'],
                row['overdue_90_plus'],
                credits,
                mark,
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

