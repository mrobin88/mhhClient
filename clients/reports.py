"""
CSV Export views and report generation for worker dispatch
"""
import csv
import io
import re
import zipfile
from datetime import date, datetime, timedelta
from html import escape
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Count

from .models import Client, CaseNote, JobPlacement
from .models_extensions import WorkAssignment, WorkSite, WorkerTimePunch
from .notifications import followup_stage


# Accountants read these reports in local time, but the DB stores UTC.
from .time_display import display_tz as _display_tz

REPORT_DISPLAY_TZ = _display_tz()


def _staff_aliases(user):
    full_name = (user.get_full_name() or '').strip()
    aliases = {user.username}
    if full_name:
        aliases.add(full_name)
    if user.email:
        aliases.add(user.email)
    return aliases


def _client_metrics_snapshot():
    return _client_metrics_snapshot_for_queryset(Client.objects.all())


def _digits_only(value):
    return re.sub(r'\D', '', value or '')


def _slug_for_filename(value):
    slug = re.sub(r'[^a-z0-9]+', '_', (value or '').lower()).strip('_')
    return slug or 'client'


def _resolve_client_lookup(raw_lookup):
    lookup = (raw_lookup or '').strip()
    if not lookup:
        return None, 'Provide a client ID, phone number, or name.'

    if lookup.isdigit():
        by_id = Client.objects.filter(pk=int(lookup)).first()
        if by_id:
            return by_id, None

    lookup_digits = _digits_only(lookup)
    if lookup_digits:
        for candidate in Client.objects.only('id', 'phone'):
            candidate_digits = _digits_only(candidate.phone)
            if not candidate_digits:
                continue
            if (
                candidate_digits == lookup_digits
                or candidate_digits.endswith(lookup_digits)
                or lookup_digits.endswith(candidate_digits)
            ):
                return candidate, None

    by_name = list(
        Client.objects.filter(
            Q(first_name__icontains=lookup)
            | Q(last_name__icontains=lookup)
            | Q(staff_name__icontains=lookup)
        ).order_by('-updated_at')[:2]
    )
    if len(by_name) == 1:
        return by_name[0], None
    if len(by_name) > 1:
        return None, 'More than one client matches that name. Try client ID or phone number.'

    return None, 'No client matched that search. Check the ID/phone/name and try again.'


def _build_client_case_narrative(client, notes):
    if not notes:
        return (
            f"{client.full_name} does not yet have case notes on file. "
            "Use this printable to start a consistent timeline for staff handoffs."
        )

    first_note = notes[0]
    last_note = notes[-1]
    note_type_counts = {}
    overdue_notes = 0
    upcoming_followups = 0
    for note in notes:
        note_type_counts[note.get_note_type_display()] = note_type_counts.get(note.get_note_type_display(), 0) + 1
        stage = followup_stage(note.follow_up_date)
        if stage in {'overdue_under_30', 'overdue_30_plus', 'overdue_60_plus', 'overdue_90_plus'}:
            overdue_notes += 1
        elif stage == 'current':
            upcoming_followups += 1

    top_note_type = max(note_type_counts.items(), key=lambda item: item[1])[0]
    job_status = 'has a job placement on record' if client.job_placed else 'does not have a recorded job placement yet'
    return (
        f"{client.full_name} entered services on {client.created_at.strftime('%Y-%m-%d')} and currently "
        f"{job_status}. Their case timeline includes {len(notes)} notes from "
        f"{first_note.note_date.strftime('%Y-%m-%d')} through {last_note.note_date.strftime('%Y-%m-%d')}, with "
        f"most activity in {top_note_type.lower()}. There are {overdue_notes} overdue follow-up items and "
        f"{upcoming_followups} upcoming follow-up items currently on file."
    )


class ReportsHubView(LoginRequiredMixin, View):
    """
    Single entry point for managers/auditors to pull reports.
    Keeps links discoverable and avoids manual URL editing.
    """

    def get(self, request):
        if not request.user.is_authenticated:
            return render(
                request,
                'clients/reports_login_required.html',
                status=403,
            )

        today = date.today().isoformat()
        start_of_month = date.today().replace(day=1).isoformat()
        return render(
            request,
            'clients/reports_hub.html',
            {
                'today': today,
                'start_of_month': start_of_month,
            },
        )


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


class WorkforceInventoryPackageView(LoginRequiredMixin, View):
    """
    One-click package for audit/reporting handoff:
      - workforce_inventory_prefill.csv
      - zip_codes_served.csv
      - printable_summary.html
    """

    def get(self, request):
        start_date_str = (request.GET.get('start_date') or '').strip()
        end_date_str = (request.GET.get('end_date') or '').strip()
        clients = Client.objects.all()

        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                clients = clients.filter(created_at__date__gte=start_date)
            except ValueError:
                return HttpResponse('Invalid start_date. Use YYYY-MM-DD.', status=400)
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                clients = clients.filter(created_at__date__lte=end_date)
            except ValueError:
                return HttpResponse('Invalid end_date. Use YYYY-MM-DD.', status=400)

        metrics = _client_metrics_snapshot_for_queryset(clients)

        # 1) Main prefill CSV (easy to copy into FY workbook)
        prefill_io = io.StringIO()
        w = csv.writer(prefill_io)
        w.writerow(['Section', 'Data Element', 'Value'])
        w.writerow(['Program', 'Program Participants ("Duplicated" Clients)', metrics['total_clients']])
        w.writerow(['Program', 'Unique Clients ("Unduplicated" Clients)', metrics['total_clients']])
        w.writerow(['Program', 'Active Clients', metrics['active_clients']])
        w.writerow([])
        w.writerow(['Gender', 'Data Element', 'Value'])
        for label, val in metrics['gender_counts'].items():
            w.writerow(['Gender', label, val])
        w.writerow([])
        w.writerow(['Age', 'Data Element', 'Value'])
        for label, val in metrics['age_counts'].items():
            w.writerow(['Age', label, val])
        w.writerow([])
        w.writerow(['Race/Ethnicity', 'Data Element', 'Value'])
        for label, val in metrics['race_counts'].items():
            w.writerow(['Race/Ethnicity', label, val])
        w.writerow([])
        w.writerow(['Program Interest', 'Program', 'Value'])
        for label, val in metrics['program_counts'].items():
            w.writerow(['Program Interest', label, val])

        # 2) ZIP summary CSV
        zip_io = io.StringIO()
        zw = csv.writer(zip_io)
        zw.writerow(['Zip Code', 'Clients Served'])
        for z, c in sorted(metrics['zip_counts'].items(), key=lambda item: (-item[1], item[0])):
            zw.writerow([z, c])

        # 3) Printable HTML summary
        def table_rows(d):
            return '\n'.join(f'<tr><td>{k}</td><td style="text-align:right;">{v}</td></tr>' for k, v in d.items())

        html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Workforce Inventory Summary</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 28px; color: #0f172a; }}
h1,h2 {{ margin-bottom: 8px; }}
table {{ border-collapse: collapse; width: 100%; margin-bottom: 18px; }}
th,td {{ border: 1px solid #cbd5e1; padding: 8px 10px; font-size: 13px; }}
th {{ background: #f1f5f9; text-align: left; }}
.meta {{ color: #475569; margin-bottom: 16px; }}
</style></head><body>
<h1>FY Workforce Services Inventory (Auto Summary)</h1>
<div class="meta">Generated: {metrics['generated_at']}</div>
<h2>Topline</h2>
<table><tr><th>Metric</th><th>Value</th></tr>
<tr><td>Total clients</td><td>{metrics['total_clients']}</td></tr>
<tr><td>Active clients</td><td>{metrics['active_clients']}</td></tr>
</table>
<h2>Gender</h2><table><tr><th>Data Element</th><th>Value</th></tr>{table_rows(metrics['gender_counts'])}</table>
<h2>Age</h2><table><tr><th>Data Element</th><th>Value</th></tr>{table_rows(metrics['age_counts'])}</table>
<h2>Race/Ethnicity</h2><table><tr><th>Data Element</th><th>Value</th></tr>{table_rows(metrics['race_counts'])}</table>
<h2>Program Interest</h2><table><tr><th>Program</th><th>Value</th></tr>{table_rows(metrics['program_counts'])}</table>
<h2>Zip Codes Served</h2><table><tr><th>Zip</th><th>Clients Served</th></tr>{table_rows(dict(sorted(metrics['zip_counts'].items(), key=lambda item: (-item[1], item[0]))))}</table>
</body></html>"""

        # Build ZIP package
        out = io.BytesIO()
        with zipfile.ZipFile(out, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('workforce_inventory_prefill.csv', prefill_io.getvalue())
            zf.writestr('zip_codes_served.csv', zip_io.getvalue())
            zf.writestr('printable_summary.html', html)

        out.seek(0)
        response = HttpResponse(out.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="workforce_inventory_package_{date.today().isoformat()}.zip"'
        return response


class ClientFilePackageView(LoginRequiredMixin, View):
    """
    One-click package for a single client file:
      - client_profile.csv
      - case_notes_timeline.csv
      - printable_client_profile.html
    """

    def get(self, request):
        lookup = (request.GET.get('client_lookup') or request.GET.get('client_id') or '').strip()
        client, error = _resolve_client_lookup(lookup)
        if error:
            return HttpResponse(f'Client lookup error: {error}', status=400)

        notes = list(client.casenotes.all().order_by('note_date', 'created_at'))
        narrative = _build_client_case_narrative(client, notes)

        profile_io = io.StringIO()
        pw = csv.writer(profile_io)
        pw.writerow(['Field', 'Value'])
        pw.writerow(['Client ID', client.id])
        pw.writerow(['Client Name', client.full_name])
        pw.writerow(['Phone', client.phone or ''])
        pw.writerow(['Email', client.email or ''])
        pw.writerow(['Case Manager', client.staff_name or ''])
        pw.writerow(['Program', client.get_training_interest_display()])
        pw.writerow(['Client Status', client.get_status_display()])
        pw.writerow(['Language', client.get_language_display()])
        pw.writerow(['Employment Status', client.get_employment_status_display()])
        pw.writerow(['Program Start Date', client.program_start_date.isoformat() if client.program_start_date else ''])
        pw.writerow(['Program Completed Date', client.program_completed_date.isoformat() if client.program_completed_date else ''])
        pw.writerow(['Job Placed', 'Yes' if client.job_placed else 'No'])
        pw.writerow(['Job Placement Date', client.job_placement_date.isoformat() if client.job_placement_date else ''])
        pw.writerow(['Total Case Notes', len(notes)])
        pw.writerow(['Generated At', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])

        notes_io = io.StringIO()
        nw = csv.writer(notes_io)
        nw.writerow([
            'Date',
            'Staff Member',
            'Note Type',
            'Case Note',
            'Next Steps',
            'Follow-up Date',
            'Follow-up Status',
        ])
        for note in notes:
            nw.writerow([
                note.note_date.strftime('%Y-%m-%d') if note.note_date else '',
                note.staff_member or '',
                note.get_note_type_display(),
                note.content or '',
                note.next_steps or '',
                note.follow_up_date.isoformat() if note.follow_up_date else '',
                followup_stage(note.follow_up_date),
            ])

        timeline_items = ''.join(
            f"""
            <tr>
              <td>{escape(note.note_date.strftime('%Y-%m-%d') if note.note_date else '')}</td>
              <td>{escape(note.get_note_type_display())}</td>
              <td>{escape(note.staff_member or '')}</td>
              <td>{escape((note.content or '').strip() or '—')}</td>
              <td>{escape((note.next_steps or '').strip() or '—')}</td>
              <td>{escape(note.follow_up_date.isoformat() if note.follow_up_date else '—')}</td>
            </tr>
            """
            for note in notes
        )
        if not timeline_items:
            timeline_items = '<tr><td colspan="6">No case notes on file yet.</td></tr>'

        html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>{escape(client.full_name)} - Printable File</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 26px; color: #0f172a; }}
    h1, h2, h3 {{ margin-bottom: 8px; }}
    .meta {{ color: #475569; margin-bottom: 16px; }}
    .narrative {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 12px; margin-bottom: 16px; line-height: 1.45; }}
    .kv {{ display: grid; grid-template-columns: 220px 1fr; gap: 6px 10px; margin-bottom: 16px; }}
    .key {{ color: #334155; font-weight: 700; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 8px; }}
    th, td {{ border: 1px solid #cbd5e1; padding: 8px 10px; vertical-align: top; font-size: 12px; }}
    th {{ background: #f1f5f9; text-align: left; }}
    @media print {{
      @page {{ margin: 0.5in; }}
    }}
  </style>
</head>
<body>
  <h1>{escape(client.full_name)}</h1>
  <div class="meta">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>

  <h2>Client Information</h2>
  <div class="kv">
    <div class="key">Client ID</div><div>{client.id}</div>
    <div class="key">Client Name</div><div>{escape(client.full_name)}</div>
    <div class="key">Phone</div><div>{escape(client.phone or '—')}</div>
    <div class="key">Email</div><div>{escape(client.email or '—')}</div>
    <div class="key">Case Manager</div><div>{escape(client.staff_name or '—')}</div>
    <div class="key">Program</div><div>{escape(client.get_training_interest_display())}</div>
    <div class="key">Status</div><div>{escape(client.get_status_display())}</div>
  </div>

  <h2>Program Timeline + Narrative</h2>
  <div class="narrative">{escape(narrative)}</div>
  <div class="kv">
    <div class="key">Program Start Date</div><div>{client.program_start_date.isoformat() if client.program_start_date else '—'}</div>
    <div class="key">Program Completed Date</div><div>{client.program_completed_date.isoformat() if client.program_completed_date else '—'}</div>
    <div class="key">Job Placement</div><div>{'Yes' if client.job_placed else 'No'}</div>
    <div class="key">Job Placement Date</div><div>{client.job_placement_date.isoformat() if client.job_placement_date else '—'}</div>
    <div class="key">Case Note Count</div><div>{len(notes)}</div>
  </div>

  <h2>Case Notes Timeline</h2>
  <table>
    <thead>
      <tr>
        <th>Date</th>
        <th>Type</th>
        <th>Staff</th>
        <th>Case Note</th>
        <th>Next Steps</th>
        <th>Follow-up Date</th>
      </tr>
    </thead>
    <tbody>
      {timeline_items}
    </tbody>
  </table>
</body>
</html>"""

        out = io.BytesIO()
        with zipfile.ZipFile(out, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('client_profile.csv', profile_io.getvalue())
            zf.writestr('case_notes_timeline.csv', notes_io.getvalue())
            zf.writestr('printable_client_profile.html', html)

        out.seek(0)
        response = HttpResponse(out.getvalue(), content_type='application/zip')
        safe_name = _slug_for_filename(client.full_name)
        response['Content-Disposition'] = (
            f'attachment; filename="client_file_package_{client.id}_{safe_name}_{date.today().isoformat()}.zip"'
        )
        return response


def _client_metrics_snapshot_for_queryset(clients):
    """
    Same metric rollups as _client_metrics_snapshot(), but for a filtered queryset.
    """
    today = date.today()

    def _age_bucket(dob):
        if not dob:
            return 'unknown'
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        if age <= 17:
            return 'youth_17_under'
        if 18 <= age <= 24:
            return 'tay_18_24'
        if 25 <= age <= 54:
            return 'adult_25_54'
        return 'older_55_plus'

    metrics = {
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_clients': clients.count(),
        'active_clients': clients.filter(status='active').count(),
        'program_counts': {},
        'gender_counts': {
            'Female': 0,
            'Male': 0,
            'Genderqueer or Gender Non-binary': 0,
            'Not listed, specified': 0,
            'Declined to state': 0,
            'Data Unknown or Unavailable.': 0,
        },
        'age_counts': {
            'Youth (17 and under)': 0,
            'TAY (age 18 to 24)': 0,
            'Adults (age 25 to 54)': 0,
            'Older Adults (age 55 and over)': 0,
            'Declined to state': 0,
            'Data Unknown or Unavailable.': 0,
        },
        'race_counts': {
            'American Indian or Alaska Native, alone': 0,
            'Asian, alone': 0,
            'Black or African-American, alone': 0,
            'Hispanic, Latino, or Spanish': 0,
            'Middle Eastern or North African, alone': 0,
            'Native Hawaiian or Other Pacific Islander, alone': 0,
            'White, alone': 0,
            'Other Race, alone': 0,
            'Two or More Races': 0,
            'Declined to state': 0,
            'Data Unknown or Unavailable.': 0,
        },
        'zip_counts': {},
    }

    for key, label in Client.TRAINING_INTEREST_CHOICES:
        metrics['program_counts'][label] = clients.filter(training_interest=key).count()

    for c in clients.only('gender', 'dob', 'demographic_info', 'zip_code'):
        if c.gender == 'F':
            metrics['gender_counts']['Female'] += 1
        elif c.gender == 'M':
            metrics['gender_counts']['Male'] += 1
        elif c.gender == 'NB':
            metrics['gender_counts']['Genderqueer or Gender Non-binary'] += 1
        elif c.gender == 'O':
            metrics['gender_counts']['Not listed, specified'] += 1
        elif c.gender == 'P':
            metrics['gender_counts']['Declined to state'] += 1
        else:
            metrics['gender_counts']['Data Unknown or Unavailable.'] += 1

        age_bucket = _age_bucket(c.dob)
        if age_bucket == 'youth_17_under':
            metrics['age_counts']['Youth (17 and under)'] += 1
        elif age_bucket == 'tay_18_24':
            metrics['age_counts']['TAY (age 18 to 24)'] += 1
        elif age_bucket == 'adult_25_54':
            metrics['age_counts']['Adults (age 25 to 54)'] += 1
        elif age_bucket == 'older_55_plus':
            metrics['age_counts']['Older Adults (age 55 and over)'] += 1
        else:
            metrics['age_counts']['Data Unknown or Unavailable.'] += 1

        if c.demographic_info in {'american_indian', 'native'}:
            metrics['race_counts']['American Indian or Alaska Native, alone'] += 1
        elif c.demographic_info == 'asian':
            metrics['race_counts']['Asian, alone'] += 1
        elif c.demographic_info == 'black':
            metrics['race_counts']['Black or African-American, alone'] += 1
        elif c.demographic_info in {'hispanic_latinx', 'latinx'}:
            metrics['race_counts']['Hispanic, Latino, or Spanish'] += 1
        elif c.demographic_info == 'middle_eastern':
            metrics['race_counts']['Middle Eastern or North African, alone'] += 1
        elif c.demographic_info == 'pacific_islander':
            metrics['race_counts']['Native Hawaiian or Other Pacific Islander, alone'] += 1
        elif c.demographic_info == 'white':
            metrics['race_counts']['White, alone'] += 1
        elif c.demographic_info in {'multiracial', 'mixed'}:
            metrics['race_counts']['Two or More Races'] += 1
        elif c.demographic_info in {'decline_state', 'prefer_not'}:
            metrics['race_counts']['Declined to state'] += 1
        elif c.demographic_info == 'other':
            metrics['race_counts']['Other Race, alone'] += 1
        else:
            metrics['race_counts']['Data Unknown or Unavailable.'] += 1

        zip_code = (c.zip_code or '').strip()
        if zip_code:
            metrics['zip_counts'][zip_code] = metrics['zip_counts'].get(zip_code, 0) + 1

    return metrics


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


def _created_range_requested(request):
    return request.GET.get('created_range') in {'1', 'true', 'True'}


def _clients_for_outcomes_report(request):
    """
    Client queryset for outcomes exports.
    By default includes ALL clients. Pass created_range=1 plus dates to limit by created_at.
    """
    case_manager = (request.GET.get('case_manager') or '').strip()
    program = (request.GET.get('program') or '').strip()
    demographic = (request.GET.get('demographic') or '').strip()
    client_status = (request.GET.get('status') or '').strip()
    mine = request.GET.get('mine')

    clients = Client.objects.annotate(
        case_notes_total=Count('casenotes'),
        documents_on_file=Count('documents'),
    )
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

    if _created_range_requested(request):
        start_date = (request.GET.get('created_start') or request.GET.get('start_date') or '').strip()
        end_date = (request.GET.get('created_end') or request.GET.get('end_date') or '').strip()
        if start_date:
            clients = clients.filter(created_at__date__gte=start_date)
        if end_date:
            clients = clients.filter(created_at__date__lte=end_date)

    return clients.order_by('-updated_at')


CLIENT_OUTCOMES_HEADERS = [
    'Client ID',
    'Client Name',
    'Phone',
    'Email',
    'Case Manager',
    'Case Manager Assigned',
    'Program',
    'Demographic Group',
    'Language',
    'Employment Status',
    'Client Status',
    'Created At',
    'Last Updated',
    'Program Start',
    'Program Completed',
    'Job Placed',
    'Job Placement Date',
    'Has Resume',
    'Documents On File',
    'Total Case Notes',
    'Last Case Note Date',
    'Follow-up Overdue Bucket',
]


def _worst_followup_bucket(notes, today=None):
    today = today or date.today()
    overdue_bucket = 'no_followup'
    rank = {
        'no_followup': 0,
        'current': 1,
        'overdue_under_30': 2,
        'overdue_30_plus': 3,
        'overdue_60_plus': 4,
        'overdue_90_plus': 5,
    }
    for note in notes:
        stage = followup_stage(note.follow_up_date, today=today)
        if rank.get(stage, 0) > rank.get(overdue_bucket, 0):
            overdue_bucket = stage
    return overdue_bucket


def _write_client_outcomes_csv(writer, clients):
    today = date.today()
    notes_by_client = {}
    for client in clients.prefetch_related('casenotes'):
        notes_by_client[client.id] = list(client.casenotes.all().order_by('-note_date', '-created_at'))

    writer.writerow(CLIENT_OUTCOMES_HEADERS)
    for client in clients:
        notes = notes_by_client.get(client.id, [])
        last_note = notes[0] if notes else None
        writer.writerow([
            client.id,
            client.full_name,
            client.phone or '',
            client.email or '',
            client.staff_name or '',
            'Yes' if (client.staff_name or '').strip() else 'No',
            client.get_training_interest_display(),
            client.get_demographic_info_display(),
            client.get_language_display(),
            client.get_employment_status_display(),
            client.get_status_display(),
            client.created_at.strftime('%Y-%m-%d') if client.created_at else '',
            client.updated_at.strftime('%Y-%m-%d') if client.updated_at else '',
            client.program_start_date.isoformat() if client.program_start_date else '',
            client.program_completed_date.isoformat() if client.program_completed_date else '',
            'Yes' if client.job_placed else 'No',
            client.job_placement_date.isoformat() if client.job_placement_date else '',
            'Yes' if client.resume else 'No',
            getattr(client, 'documents_on_file', 0) or 0,
            getattr(client, 'case_notes_total', len(notes)),
            last_note.note_date.strftime('%Y-%m-%d') if last_note and last_note.note_date else '',
            _worst_followup_bucket(notes, today=today),
        ])


def _build_client_outcomes_summary_html(clients, request):
    metrics = _client_metrics_snapshot_for_queryset(clients)
    unassigned = clients.filter(Q(staff_name__isnull=True) | Q(staff_name='')).count()
    no_notes = clients.filter(case_notes_total=0).count()
    created_filter = 'Yes (created date range applied)' if _created_range_requested(request) else 'No (all clients in system)'

    rows = []
    for client in clients[:500]:
        rows.append(
            f'<tr><td>{client.id}</td><td>{escape(client.full_name)}</td>'
            f'<td>{escape(client.staff_name or "—")}</td><td>{escape(client.get_status_display())}</td>'
            f'<td>{getattr(client, "case_notes_total", 0)}</td></tr>'
        )
    if not rows:
        rows.append('<tr><td colspan="5">No clients matched these filters.</td></tr>')
    more = ''
    if clients.count() > 500:
        more = f'<p class="meta">Showing first 500 of {clients.count()} clients. Open the CSV in the package for the full list.</p>'

    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Client Outcomes Summary</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 24px; color: #0f172a; }}
h1,h2 {{ margin-bottom: 8px; }}
.meta {{ color: #475569; margin-bottom: 14px; line-height: 1.45; }}
table {{ border-collapse: collapse; width: 100%; margin-top: 10px; font-size: 12px; }}
th,td {{ border: 1px solid #cbd5e1; padding: 6px 8px; text-align: left; }}
th {{ background: #f1f5f9; }}
.box {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 12px; margin-bottom: 14px; }}
@media print {{ @page {{ margin: 0.5in; }} }}
</style></head><body>
<h1>Client Outcomes Summary</h1>
<p class="meta">Generated {metrics['generated_at']}. Created-date filter: {created_filter}.</p>
<div class="box">
  <strong>Topline</strong><br>
  Clients in this export: <strong>{metrics['total_clients']}</strong><br>
  Active: <strong>{metrics['active_clients']}</strong><br>
  Missing case manager: <strong>{unassigned}</strong><br>
  No case notes on file: <strong>{no_notes}</strong>
</div>
<p class="meta"><strong>Tip:</strong> Use the CSV in this package for Excel. Print this page for a quick staff meeting handout.</p>
{more}
<h2>Client list (snapshot)</h2>
<table>
  <thead><tr><th>ID</th><th>Name</th><th>Case Manager</th><th>Status</th><th>Notes</th></tr></thead>
  <tbody>{''.join(rows)}</tbody>
</table>
</body></html>"""


class ClientOutcomesReportCSVView(LoginRequiredMixin, View):
    """
    Export client-level outcomes report for OEWD/state reporting.
    Includes all clients unless created_range=1 with optional date bounds.
    """

    def get(self, request):
        clients = _clients_for_outcomes_report(request)
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = (
            f'attachment; filename="client_outcomes_{date.today().isoformat()}.csv"'
        )
        writer = csv.writer(response)
        _write_client_outcomes_csv(writer, clients)
        return response


class ClientOutcomesPackageView(LoginRequiredMixin, View):
    """ZIP: outcomes CSV + printable HTML summary (easier than raw CSV alone)."""

    def get(self, request):
        clients = _clients_for_outcomes_report(request)
        csv_io = io.StringIO()
        _write_client_outcomes_csv(csv.writer(csv_io), clients)
        html = _build_client_outcomes_summary_html(clients, request)
        readme = (
            'Client Outcomes Package\n'
            '========================\n'
            '1) Open client_outcomes.csv in Excel or Google Sheets.\n'
            '2) Print client_outcomes_summary.html for a quick snapshot.\n'
            f'Total clients in this export: {clients.count()}\n'
            'Note: By default this includes ALL clients. Use Reports Hub checkbox '
            '"Only clients created in date range" to narrow.\n'
        )

        out = io.BytesIO()
        with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('README.txt', readme)
            zf.writestr(f'client_outcomes_{date.today().isoformat()}.csv', csv_io.getvalue())
            zf.writestr('client_outcomes_summary.html', html)
        out.seek(0)
        response = HttpResponse(out.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = (
            f'attachment; filename="client_outcomes_package_{date.today().isoformat()}.zip"'
        )
        return response


class ManagerOperationsPackageView(LoginRequiredMixin, View):
    """
    One-click manager bundle: outcomes package + follow-up scorecard + PitStop hours.
    """

    def get(self, request):
        clients = _clients_for_outcomes_report(request)
        since_days = int(request.GET.get('since_days', '90') or 90)
        since_date = date.today() - timedelta(days=since_days)

        outcomes_csv = io.StringIO()
        _write_client_outcomes_csv(csv.writer(outcomes_csv), clients)
        outcomes_html = _build_client_outcomes_summary_html(clients, request)

        score_io = io.StringIO()
        score_writer = csv.writer(score_io)
        score_writer.writerow([
            'Staff Member', 'Total Notes', 'Follow-up Notes', 'Clients Touched',
            'Overdue 30+', 'Overdue 60+', 'Overdue 90+', 'Credits', 'Mark',
        ])
        notes = CaseNote.objects.filter(note_date__gte=since_date).select_related('client')
        if request.GET.get('mine') in {'1', 'true', 'True'}:
            notes = notes.filter(staff_member__in=_staff_aliases(request.user))
        scorecard = {}
        for note in notes:
            key = (note.staff_member or 'Unassigned').strip() or 'Unassigned'
            if key not in scorecard:
                scorecard[key] = {
                    'total_notes': 0, 'follow_up_notes': 0, 'clients_touched': set(),
                    'overdue_30_plus': 0, 'overdue_60_plus': 0, 'overdue_90_plus': 0,
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
        for staff_member, row in sorted(scorecard.items(), key=lambda item: item[0].lower()):
            credits = (
                (row['follow_up_notes'] * 3) + row['total_notes']
                - (row['overdue_30_plus'] * 2) - (row['overdue_60_plus'] * 3)
                - (row['overdue_90_plus'] * 4)
            )
            mark = 'A' if credits >= 80 else 'B' if credits >= 50 else 'C' if credits >= 25 else 'D'
            score_writer.writerow([
                staff_member, row['total_notes'], row['follow_up_notes'], len(row['clients_touched']),
                row['overdue_30_plus'], row['overdue_60_plus'], row['overdue_90_plus'], credits, mark,
            ])

        pitstop_io = io.StringIO()
        start_date = (request.GET.get('start_date') or '').strip()
        end_date = (request.GET.get('end_date') or '').strip()
        if not start_date:
            start_date = (date.today() - timedelta(days=14)).isoformat()
        if not end_date:
            end_date = date.today().isoformat()
        punches = WorkerTimePunch.objects.select_related(
            'worker_account__client', 'work_site'
        ).order_by('-clock_in_at')
        punches = punches.filter(clock_in_at__date__gte=start_date, clock_in_at__date__lte=end_date)
        write_pitstop_hours_csv(pitstop_io, punches)

        start_here = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Manager Package</title>
<style>body{{font-family:Arial,sans-serif;margin:28px;color:#0f172a;line-height:1.5}}
h1{{margin-bottom:6px}}.step{{margin:10px 0;padding:10px 14px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px}}
</style></head><body>
<h1>Manager Operations Package</h1>
<p>Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}. Unzip this folder, then:</p>
<div class="step"><strong>1.</strong> Open <code>client_outcomes.csv</code> in Excel — full caseload ({clients.count()} clients).</div>
<div class="step"><strong>2.</strong> Print <code>client_outcomes_summary.html</code> for a one-page meeting snapshot.</div>
<div class="step"><strong>3.</strong> Review <code>staff_followup_scorecard.csv</code> (last {since_days} days).</div>
<div class="step"><strong>4.</strong> Review <code>pitstop_hours.csv</code> for clocked time (uses activity date range from Reports Hub).</div>
</body></html>"""

        out = io.BytesIO()
        with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('START_HERE.html', start_here)
            zf.writestr(f'client_outcomes_{date.today().isoformat()}.csv', outcomes_csv.getvalue())
            zf.writestr('client_outcomes_summary.html', outcomes_html)
            zf.writestr('staff_followup_scorecard.csv', score_io.getvalue())
            zf.writestr('pitstop_hours.csv', pitstop_io.getvalue())
        out.seek(0)
        response = HttpResponse(out.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = (
            f'attachment; filename="manager_operations_package_{date.today().isoformat()}.zip"'
        )
        return response


class JobPlacementsReportCSVView(LoginRequiredMixin, View):
    """
    Export job placements for audit and manager review.
    GET parameters:
      - start_date (required-ish for audit windows)
      - end_date
      - work_type (full_time|part_time|contract)
      - mine=1 (placements logged by current user)
      - logged_by (string contains filter on logger name)
    """

    def get(self, request):
        start_date = (request.GET.get('start_date') or '').strip()
        end_date = (request.GET.get('end_date') or '').strip()
        work_type = (request.GET.get('work_type') or '').strip()
        mine = request.GET.get('mine')
        logged_by = (request.GET.get('logged_by') or '').strip()

        placements = JobPlacement.objects.select_related('client', 'created_by_user').all()
        if start_date:
            placements = placements.filter(start_date__gte=start_date)
        if end_date:
            placements = placements.filter(start_date__lte=end_date)
        if work_type:
            placements = placements.filter(work_type=work_type)
        if mine in {'1', 'true', 'True'}:
            aliases = _staff_aliases(request.user)
            placements = placements.filter(
                Q(created_by_user=request.user) | Q(created_by_name__in=aliases)
            )
        elif logged_by:
            placements = placements.filter(created_by_name__icontains=logged_by)

        response = HttpResponse(content_type='text/csv')
        filename_suffix = f"{start_date or 'all'}_to_{end_date or 'all'}"
        response['Content-Disposition'] = (
            f'attachment; filename="job_placements_{filename_suffix}.csv"'
        )
        writer = csv.writer(response)
        writer.writerow([
            'Placement ID',
            'Client ID',
            'Client Name',
            'Client Phone',
            'Employer',
            'Job Title',
            'Work Type',
            'Hourly Rate',
            'Start Date',
            'Employer Address',
            'Logged By',
            'Logged At',
            'Notes',
        ])
        for p in placements.order_by('-start_date', '-created_at'):
            writer.writerow([
                p.id,
                p.client_id,
                p.client.full_name,
                p.client.phone or '',
                p.employer,
                p.job_title or '',
                p.get_work_type_display(),
                p.hourly_rate if p.hourly_rate is not None else '',
                p.start_date.isoformat() if p.start_date else '',
                p.employer_address or '',
                p.created_by_name or (p.created_by_user.username if p.created_by_user else ''),
                p.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                p.notes or '',
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

        notes = CaseNote.objects.filter(note_date__gte=since_date).select_related('client')
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


# Columns ordered for accountant/staff review: who → each punch with its
# location → hours → verification → audit references. Every backend data point
# from the punch is preserved (lat/long, geo status notes, IDs).
PITSTOP_HOURS_CSV_HEADER = [
    'Worker Name',
    'Date',
    'Clock In',
    'Clock In Longitude',
    'Clock In Latitude',
    'Clock Out',
    'Clock Out Longitude',
    'Clock Out Latitude',
    'Gross Hours',
    'Lunch Out',
    'Lunch In',
    'Lunch (min)',
    'Net Hours',
    'Short Shift?',
    'Status',
    'Work Site',
    'Clock In Location Verified',
    'Clock Out Location Verified',
    'Clock In Note',
    'Clock Out Note',
    'Worker Phone',
    'Worker ID',
    'Punch ID',
]


def _short_shift_threshold():
    return float(getattr(settings, 'WORKER_SHORT_SHIFT_HOURS', 7.0))


def _pitstop_punch_hours(punch):
    if not punch.clock_in_at or not punch.clock_out_at:
        return None
    seconds = max((punch.clock_out_at - punch.clock_in_at).total_seconds(), 0)
    return round(seconds / 3600, 2)


def _local_date(value):
    if not value:
        return ''
    return value.astimezone(REPORT_DISPLAY_TZ).strftime('%Y-%m-%d')


def _local_time_12h(value):
    if not value:
        return ''
    # %I gives a zero-padded 12-hour hour; strip the leading zero for readability.
    formatted = value.astimezone(REPORT_DISPLAY_TZ).strftime('%I:%M %p')
    return formatted[1:] if formatted.startswith('0') else formatted


def _format_punch_row(punch):
    gross_hours = _pitstop_punch_hours(punch)
    net_hours = punch.net_hours
    lunch_minutes = punch.lunch_minutes
    worker_client = getattr(punch.worker_account, 'client', None) if punch.worker_account else None
    status = 'Complete' if punch.clock_out_at else 'Still clocked in'

    if net_hours is None:
        short_shift = ''  # open punch — nothing to judge yet
    else:
        short_shift = 'Yes' if net_hours < _short_shift_threshold() else 'No'

    return [
        worker_client.full_name if worker_client else '',
        _local_date(punch.clock_in_at),
        _local_time_12h(punch.clock_in_at),
        f'{punch.clock_in_longitude}' if punch.clock_in_longitude is not None else '',
        f'{punch.clock_in_latitude}' if punch.clock_in_latitude is not None else '',
        _local_time_12h(punch.clock_out_at),
        f'{punch.clock_out_longitude}' if punch.clock_out_longitude is not None else '',
        f'{punch.clock_out_latitude}' if punch.clock_out_latitude is not None else '',
        f'{gross_hours:.2f}' if gross_hours is not None else '',
        _local_time_12h(punch.lunch_start_at),
        _local_time_12h(punch.lunch_end_at),
        lunch_minutes if lunch_minutes else '',
        f'{net_hours:.2f}' if net_hours is not None else '',
        short_shift,
        status,
        punch.work_site.name if punch.work_site else '',
        'Yes' if punch.clock_in_geo_basic_ok else 'No',
        'Yes' if punch.clock_out_geo_basic_ok else ('No' if punch.clock_out_at else ''),
        punch.clock_in_geo_basic_note or '',
        punch.clock_out_geo_basic_note or '',
        (getattr(worker_client, 'phone', '') or getattr(punch.worker_account, 'phone', '') or '') if punch.worker_account else '',
        punch.worker_account_id or '',
        punch.pk,
    ]


def write_pitstop_hours_csv(stream, punches):
    writer = csv.writer(stream)
    writer.writerow(PITSTOP_HOURS_CSV_HEADER)
    for punch in punches:
        writer.writerow(_format_punch_row(punch))
    return stream


class PitStopHoursReportCSVView(LoginRequiredMixin, View):
    """
    Export CSV of PitStop hours (clock in/out punches) for payroll-style review.
    GET parameters:
        - start_date (YYYY-MM-DD, default: today minus 14 days)
        - end_date (YYYY-MM-DD, default: today)
        - work_site_id
        - worker_id
        - only_complete=1 (exclude open punches)
        - min_hours (decimal)
    """

    def get(self, request):
        today = date.today()
        default_start = today - timedelta(days=14)
        start_date_str = (request.GET.get('start_date') or default_start.isoformat()).strip()
        end_date_str = (request.GET.get('end_date') or today.isoformat()).strip()
        work_site_id = (request.GET.get('work_site_id') or '').strip()
        worker_id = (request.GET.get('worker_id') or '').strip()
        only_complete = request.GET.get('only_complete') in {'1', 'true', 'True'}
        min_hours_raw = (request.GET.get('min_hours') or '').strip()

        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            return HttpResponse('Invalid start_date. Use YYYY-MM-DD.', status=400)
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            return HttpResponse('Invalid end_date. Use YYYY-MM-DD.', status=400)

        punches = (
            WorkerTimePunch.objects.filter(
                clock_in_at__date__gte=start_date,
                clock_in_at__date__lte=end_date,
            )
            .select_related('worker_account__client', 'work_site')
            .order_by('-clock_in_at')
        )
        if work_site_id:
            punches = punches.filter(work_site_id=work_site_id)
        if worker_id:
            punches = punches.filter(worker_account_id=worker_id)
        if only_complete:
            punches = punches.exclude(clock_out_at__isnull=True)

        min_hours_value = None
        if min_hours_raw:
            try:
                min_hours_value = float(min_hours_raw)
            except ValueError:
                return HttpResponse('Invalid min_hours. Use a decimal value.', status=400)

        if min_hours_value is not None:
            kept = []
            for punch in punches:
                hours = _pitstop_punch_hours(punch)
                if hours is not None and hours >= min_hours_value:
                    kept.append(punch)
            punches = kept

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = (
            f'attachment; filename="pitstop_hours_{start_date.isoformat()}_to_{end_date.isoformat()}.csv"'
        )
        write_pitstop_hours_csv(response, punches)
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

