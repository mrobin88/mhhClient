"""
CSV Export views and report generation for worker dispatch
"""
import csv
import io
import zipfile
from datetime import date, datetime, timedelta
from django.http import HttpResponse
from django.shortcuts import render
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Count

from .models import Client, CaseNote, JobPlacement
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


def _client_metrics_snapshot():
    return _client_metrics_snapshot_for_queryset(Client.objects.all())


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
        html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Reports Hub</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; color: #0f172a; background: #f8fafc; }}
    h1 {{ margin-bottom: 4px; }}
    .sub {{ color: #475569; margin-bottom: 18px; }}
    .row {{ display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 14px; }}
    input {{ padding: 8px 10px; border: 1px solid #cbd5e1; border-radius: 8px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 12px; }}
    .card {{ background: #fff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 14px; }}
    .title {{ font-weight: 700; margin-bottom: 8px; }}
    .desc {{ color: #475569; font-size: 14px; margin-bottom: 10px; }}
    a.btn {{ display: inline-block; background: #0f766e; color: #fff; text-decoration: none; padding: 8px 10px; border-radius: 8px; font-size: 13px; }}
    a.secondary {{ background: #334155; margin-left: 6px; }}
  </style>
</head>
<body>
  <h1>Reports Hub</h1>
  <div class="sub">Pull manager and audit exports from one place.</div>

  <div class="row">
    <label>Start date <input id="startDate" type="date" value="{start_of_month}"></label>
    <label>End date <input id="endDate" type="date" value="{today}"></label>
  </div>

  <div class="grid">
    <div class="card">
      <div class="title">Client Outcomes</div>
      <div class="desc">Case manager, program, demographics, and outcome tracking.</div>
      <a class="btn" id="clientOutcomesCsv" href="/api/reports/client-outcomes/" target="_blank">Download CSV</a>
    </div>
    <div class="card">
      <div class="title">Job Placements</div>
      <div class="desc">Who got placed, where, pay, work type, start date, and who logged it.</div>
      <a class="btn" id="jobPlacementsCsv" href="/api/reports/job-placements/" target="_blank">Download CSV</a>
    </div>
    <div class="card">
      <div class="title">Workforce Inventory Package</div>
      <div class="desc">ZIP package with printable summary, demographic counts, and zip codes served.</div>
      <a class="btn" id="workforceZip" href="/api/reports/workforce-inventory-package/" target="_blank">Download ZIP</a>
    </div>
    <div class="card">
      <div class="title">Staff Follow-up Scorecard</div>
      <div class="desc">Follow-up volume and 30/60/90+ overdue buckets by staff member.</div>
      <a class="btn" href="/api/reports/staff-followup-scorecard/" target="_blank">Download CSV</a>
      <a class="btn secondary" href="/api/reports/staff-followup-scorecard/?since_days=30" target="_blank">Last 30 days</a>
    </div>
    <div class="card">
      <div class="title">Call-outs</div>
      <div class="desc">Attendance risk and same-day coverage pressure.</div>
      <a class="btn" id="calloutsCsv" href="/api/reports/callouts/" target="_blank">Download CSV</a>
    </div>
    <div class="card">
      <div class="title">Today's Assignments</div>
      <div class="desc">Current day roster snapshot.</div>
      <a class="btn" href="/api/reports/todays-assignments/" target="_blank">Download CSV</a>
    </div>
  </div>

  <script>
    const startEl = document.getElementById('startDate');
    const endEl = document.getElementById('endDate');
    const withRange = (base) => {{
      const start = encodeURIComponent(startEl.value || '');
      const end = encodeURIComponent(endEl.value || '');
      const sep = base.includes('?') ? '&' : '?';
      return `${{base}}${{sep}}start_date=${{start}}&end_date=${{end}}`;
    }};
    const applyLinks = () => {{
      document.getElementById('clientOutcomesCsv').href = withRange('/api/reports/client-outcomes/');
      document.getElementById('jobPlacementsCsv').href = withRange('/api/reports/job-placements/');
      document.getElementById('workforceZip').href = withRange('/api/reports/workforce-inventory-package/');
      document.getElementById('calloutsCsv').href = withRange('/api/reports/callouts/');
    }};
    startEl.addEventListener('change', applyLinks);
    endEl.addEventListener('change', applyLinks);
    applyLinks();
  </script>
</body>
</html>"""
        return HttpResponse(html, content_type='text/html')


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


class ClientOutcomesReportCSVView(LoginRequiredMixin, View):
    """
    Export client-level outcomes report for OEWD/state reporting.
    GET parameters:
      - case_manager
      - program
      - demographic
      - status
      - start_date (YYYY-MM-DD, client created range)
      - end_date (YYYY-MM-DD, client created range)
      - mine=1 (limit to current logged-in staff aliases)
    """

    def get(self, request):
        case_manager = (request.GET.get('case_manager') or '').strip()
        program = (request.GET.get('program') or '').strip()
        demographic = (request.GET.get('demographic') or '').strip()
        client_status = (request.GET.get('status') or '').strip()
        start_date = (request.GET.get('start_date') or '').strip()
        end_date = (request.GET.get('end_date') or '').strip()
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
        if start_date:
            clients = clients.filter(created_at__date__gte=start_date)
        if end_date:
            clients = clients.filter(created_at__date__lte=end_date)

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

