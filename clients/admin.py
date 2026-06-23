from django.contrib import admin
from django.db import connection
from django.utils.html import format_html, format_html_join
from django.urls import reverse
from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.db.models import Count, Q
from datetime import datetime, time, timedelta
import csv
import io
import logging
import os
import traceback

admin_diag_logger = logging.getLogger('config.admin_errors')
from django.shortcuts import redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.utils import timezone
from .time_display import format_display_datetime
from .models import Client, CaseNote, CityBuildFileChecklist, Document, PitStopApplication
from .models_extensions import (
    WorkSite,
    WorkerAccount,
    WorkerDailyFeedback,
    WorkerTimePunch,
    ClientTextMessage,
)
from .phone_utils import default_worker_pin_from_phone, normalize_login_phone
from .citybuild_docs import (
    CITYBUILD_PROGRAMS,
    CITYBUILD_CHECKLIST_DOC_TYPES,
    CITYBUILD_UPLOAD_DOC_TYPES,
    CITYBUILD_CHECKLIST_PANELS,
    checklist_label_for_doc_type,
    citybuild_item_present,
    citybuild_packet_for_client,
    is_citybuild_client,
)

# Document checklist on client profile (no blob calls until download).
CASE_NOTE_INLINE_LIMIT = 40

CLIENT_DOC_CHECKLIST = (
    ('resume', 'Resume'),
    ('id', 'Government ID'),
    ('consent', 'Consent Form'),
    ('intake', 'Intake Form'),
    ('sf_residency', 'Proof of SF Residency'),
    ('hs_diploma', 'HS Diploma / GED'),
    ('photo_release', 'Photo Release'),
)


def _staff_display_name(user):
    """Display name used for case notes, client credit, and audit fields."""
    from .staff_utils import staff_display_name
    return staff_display_name(user)


_CASENOTE_NOTE_DATE_COLUMN = None


def _casenote_note_date_column_exists():
    """True when migration 0029 has been applied (avoids 500s during deploy lag)."""
    global _CASENOTE_NOTE_DATE_COLUMN
    if _CASENOTE_NOTE_DATE_COLUMN is not None:
        return _CASENOTE_NOTE_DATE_COLUMN
    try:
        table = CaseNote._meta.db_table
        with connection.cursor() as cursor:
            description = connection.introspection.get_table_description(cursor, table)
        _CASENOTE_NOTE_DATE_COLUMN = any(col.name == 'note_date' for col in description)
    except Exception:
        _CASENOTE_NOTE_DATE_COLUMN = False
    return _CASENOTE_NOTE_DATE_COLUMN


def _current_week_bounds():
    today = timezone.localdate()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=7)
    start_dt = timezone.make_aware(datetime.combine(week_start, time.min))
    end_dt = timezone.make_aware(datetime.combine(week_end, time.min))
    return start_dt, end_dt


def _format_hours(hours):
    return f'{hours:.2f} hrs'


def _punch_duration_hours(punch):
    if not punch.clock_in_at or not punch.clock_out_at:
        return 0
    seconds = max((punch.clock_out_at - punch.clock_in_at).total_seconds(), 0)
    return seconds / 3600


def _weekly_hours_for_worker(account):
    if not account or not account.pk:
        return 0
    week_start, week_end = _current_week_bounds()
    punches = WorkerTimePunch.objects.filter(
        worker_account=account,
        clock_in_at__gte=week_start,
        clock_in_at__lt=week_end,
    ).exclude(clock_out_at__isnull=True)
    return sum(_punch_duration_hours(punch) for punch in punches)


def _total_hours_for_worker(account):
    if not account or not account.pk:
        return 0
    punches = WorkerTimePunch.objects.filter(worker_account=account).exclude(clock_out_at__isnull=True)
    return sum(_punch_duration_hours(punch) for punch in punches)


def _last_assignment_for_worker(account):
    if not account or not account.pk:
        return None
    return WorkerTimePunch.objects.filter(worker_account=account).select_related('work_site').order_by('-clock_in_at').first()


class CaseNoteInline(admin.TabularInline):
    """Inline admin for displaying case notes as a timestamped list on Client admin page"""
    model = CaseNote
    extra = 0
    readonly_fields = ['entered_at_display']
    fields = ['note_date', 'note_type', 'content', 'next_steps', 'entered_at_display']
    ordering = ['-note_date', '-created_at']
    can_delete = True
    verbose_name = 'Case Note'
    verbose_name_plural = 'Recent case notes (set Note date for retroactive entry)'

    def get_fields(self, request, obj=None):
        fields = list(super().get_fields(request, obj))
        if not _casenote_note_date_column_exists():
            return [field for field in fields if field != 'note_date']
        return fields

    def get_ordering(self, request):
        if _casenote_note_date_column_exists():
            return ['-note_date', '-created_at']
        return ['-created_at']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not _casenote_note_date_column_exists():
            qs = qs.defer('note_date')
        if _casenote_note_date_column_exists():
            qs = qs.order_by('-note_date', '-created_at')
        else:
            qs = qs.order_by('-created_at')
        recent_pks = list(qs.values_list('pk', flat=True)[:CASE_NOTE_INLINE_LIMIT])
        if not recent_pks:
            return qs.none()
        return qs.filter(pk__in=recent_pks)

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj and obj.pk:
            readonly.append('entered_at_display')
        return readonly

    def entered_at_display(self, obj):
        if not obj or not obj.pk or not obj.created_at:
            return format_html('<em style="color:#999;">—</em>')
        return format_html(
            '<span style="color:#64748b;font-size:11px;" title="When saved in system">Entered {}</span>',
            format_display_datetime(obj.created_at, '%m/%d/%Y %I:%M %p'),
        )
    entered_at_display.short_description = 'System'
    
    class Media:
        css = {
            'all': ()
        }
        js = ()
    
    def has_add_permission(self, request, obj=None):
        """Allow adding new case notes"""
        return True
    
    def has_change_permission(self, request, obj=None):
        """Allow editing case notes"""
        return True


@admin.register(CaseNote)
class CaseNoteAdmin(admin.ModelAdmin):
    list_display = ['formatted_date', 'client', 'note_type', 'content_preview']
    list_filter = ['note_type', 'staff_member', 'note_date']
    search_fields = ['client__first_name', 'client__last_name', 'content', 'staff_member']
    date_hierarchy = 'note_date'
    readonly_fields = ['created_at', 'updated_at', 'staff_member_display']

    def get_date_hierarchy(self, request):
        if _casenote_note_date_column_exists():
            return 'note_date'
        return 'created_at'

    def get_list_filter(self, request):
        filters = list(super().get_list_filter(request))
        if not _casenote_note_date_column_exists():
            return [f for f in filters if f != 'note_date']
        return filters

    list_per_page = 50
    
    fieldsets = (
        ('Client Information', {
            'fields': ('client', 'staff_member_display')
        }),
        ('Note Details', {
            'fields': ('note_date', 'note_type', 'content', 'next_steps'),
            'description': '⚠️ IMPORTANT: Each case note should be ONE entry. Set Note date to when the interaction happened (retroactive entry is OK).',
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    actions = ['export_to_csv']
    
    def export_to_csv(self, request, queryset):
        """Export selected case notes to CSV format"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="case_notes_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        
        # Write header row
        writer.writerow([
            'Case Note ID',
            'Client Name',
            'Client Phone',
            'Client Email',
            'Note Type',
            'Staff Member',
            'Content',
            'Next Steps',
            'Note Date',
            'Entered At (system)',
            'Updated At'
        ])
        
        # Write data rows
        for note in queryset.select_related('client'):
            writer.writerow([
                note.id,
                note.client.full_name,
                note.client.phone,
                note.client.email or '',
                note.get_note_type_display(),
                note.staff_member,
                note.content,
                note.next_steps or '',
                note.note_date.strftime('%Y-%m-%d') if note.note_date else '',
                format_display_datetime(note.created_at, '%Y-%m-%d %H:%M:%S') if note.created_at else '',
                format_display_datetime(note.updated_at, '%Y-%m-%d %H:%M:%S') if note.updated_at else '',
            ])
        
        self.message_user(request, f'✅ Exported {queryset.count()} case note(s) to CSV')
        return response
    
    export_to_csv.short_description = "Download selected case notes in CSV"
    
    def formatted_date(self, obj):
        if obj.note_date:
            return obj.note_date.strftime('%Y-%m-%d')
        return '-'
    formatted_date.short_description = 'Note date'
    formatted_date.admin_order_field = 'note_date'
    
    def content_preview(self, obj):
        """Display content preview (first 100 chars)"""
        if obj.content:
            preview = obj.content[:100]
            if len(obj.content) > 100:
                preview += '...'
            return preview
        return '-'
    content_preview.short_description = 'Note'
    
    def staff_member_display(self, obj):
        if obj and (obj.staff_member or '').strip():
            return obj.staff_member
        return format_html('<span style="color:#64748b;">Set automatically when you save</span>')
    staff_member_display.short_description = 'Staff member'

    def save_model(self, request, obj, form, change):
        """Credit new case notes to the logged-in staff member."""
        if not change:
            obj.staff_member = _staff_display_name(request.user)
        super().save_model(request, obj, form, change)
    
@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'phone', 'email', 'training_interest', 'status', 'program_completed_date', 'has_resume', 'case_notes_count', 'created_at']
    list_filter = ['status', 'training_interest', 'neighborhood', 'sf_resident', 'employment_status', 'created_at', 'program_completed_date']
    search_fields = ['first_name', 'last_name', 'phone', 'email']
    readonly_fields = [
        'created_at',
        'updated_at',
        'case_notes_count',
        'case_notes_manage_link',
        'masked_ssn',
        'documents_checklist',
        'documents_hub_link',
        'citybuild_files_summary',
        'resume_download_link',
        'worker_portal_summary',
        'staff_name',
    ]
    date_hierarchy = 'created_at'
    inlines = [CaseNoteInline]
    list_per_page = 25
    show_full_result_count = False

    def get_search_results(self, request, queryset, search_term):
        """Autocomplete from PitStop worker/application forms: PitStop clients only."""
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        model_name = (request.GET.get('model_name') or '').lower()
        field_name = (request.GET.get('field_name') or '').lower()
        if field_name == 'client' and model_name in ('workeraccount', 'pitstopapplication'):
            queryset = queryset.filter(training_interest='pit_stop')
        return queryset, use_distinct
    
    def get_urls(self):
        """Add custom URL for quick case note addition"""
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                '<path:object_id>/add-case-note/',
                self.admin_site.admin_view(self.add_case_note_view),
                name='clients_client_add_case_note',
            ),
            path(
                '<path:object_id>/documents/',
                self.admin_site.admin_view(self.client_documents_view),
                name='clients_client_documents',
            ),
            path(
                '<path:object_id>/diagnostics/',
                self.admin_site.admin_view(self.client_change_diagnostics_view),
                name='clients_client_diagnostics',
            ),
        ]
        return custom_urls + urls

    def change_view(self, request, object_id, form_url='', extra_context=None):
        try:
            return super().change_view(request, object_id, form_url, extra_context)
        except Exception:
            admin_diag_logger.exception(
                'ClientAdmin.change_view failed for client_id=%s path=%s',
                object_id,
                request.path,
            )
            raise

    def client_change_diagnostics_view(self, request, object_id):
        """Superuser-only: run change-page steps in isolation to find 500 cause."""
        from django.shortcuts import get_object_or_404
        from django.template.response import TemplateResponse
        from django.core.exceptions import PermissionDenied

        if not request.user.is_superuser:
            raise PermissionDenied

        client = get_object_or_404(Client, pk=object_id)
        self._current_request = request
        checks = []

        def run_check(label, fn):
            try:
                result = fn()
                detail = result if isinstance(result, str) else repr(result)
                if len(detail) > 500:
                    detail = detail[:500] + '…'
                checks.append({'label': label, 'ok': True, 'detail': detail or '(empty)'})
            except Exception as exc:
                checks.append({
                    'label': label,
                    'ok': False,
                    'detail': f'{type(exc).__name__}: {exc}\n{traceback.format_exc()[-800:]}',
                })

        run_check('note_date column in database', _casenote_note_date_column_exists)
        run_check('load client row', lambda: f'{client.full_name} / status={client.status}')
        run_check('case notes count', lambda: client.casenotes.count())
        run_check(
            'case note inline formset',
            lambda: CaseNoteInline(self, self.admin_site).get_formset(request, client).queryset.count(),
        )
        run_check('documents_checklist', lambda: 'rendered' if self.documents_checklist(client) else 'empty')
        run_check('documents_hub_link', lambda: 'rendered' if self.documents_hub_link(client) else 'empty')
        run_check('resume_download_link', lambda: 'rendered' if self.resume_download_link(client) else 'empty')
        run_check('case_notes_manage_link', lambda: 'rendered' if self.case_notes_manage_link(client) else 'empty')
        run_check('worker_portal_summary', lambda: 'rendered' if self.worker_portal_summary(client) else 'empty')
        run_check('masked_ssn / ssn field', lambda: str(self.masked_ssn(client))[:80])
        run_check('get_fieldsets', lambda: len(self.get_fieldsets(request, client)))

        context = {
            **self.admin_site.each_context(request),
            'title': f'Diagnostics — {client.full_name}',
            'client': client,
            'checks': checks,
            'change_url': reverse('admin:clients_client_change', args=[client.pk]),
            'opts': self.model._meta,
        }
        return TemplateResponse(request, 'admin/clients/client_change_diagnostics.html', context)

    def get_inline_instances(self, request, obj=None):
        """
        Keep add form lean: hide inlines until the client is created.
        This avoids rendering heavy inline formsets on /admin/clients/client/add/.
        """
        if obj is None:
            return []
        return super().get_inline_instances(request, obj)

    def save_formset(self, request, form, formset, change):
        """
        Ensure Document.uploaded_by is populated when adding docs from the Client page.
        """
        instances = formset.save(commit=False)
        staff_name = _staff_display_name(request.user)
        for inst in instances:
            if isinstance(inst, Document) and not inst.pk:
                inst.uploaded_by = staff_name
            if isinstance(inst, CaseNote) and not inst.pk:
                inst.staff_member = staff_name
            inst.save()
        formset.save_m2m()

    def save_model(self, request, obj, form, change):
        """Credit clients to the logged-in staff member (non-admin); kiosk/public excluded."""
        from .staff_utils import apply_staff_assignment_to_client, staff_skips_client_auto_assign

        if change:
            apply_staff_assignment_to_client(obj, request.user)
        elif not (obj.staff_name or '').strip() and not staff_skips_client_auto_assign(request.user):
            obj.staff_name = _staff_display_name(request.user)
        super().save_model(request, obj, form, change)
    
    def add_case_note_view(self, request, object_id):
        """Quick add case note view"""
        from django.shortcuts import get_object_or_404, redirect
        from django.contrib import messages
        from django.template.response import TemplateResponse
        
        client = get_object_or_404(Client, pk=object_id)
        
        if request.method == 'POST':
            try:
                from datetime import datetime as dt
                note_date_raw = (request.POST.get('note_date') or '').strip()
                note_date = None
                if note_date_raw:
                    note_date = dt.strptime(note_date_raw, '%Y-%m-%d').date()
                note = CaseNote.objects.create(
                    client=client,
                    staff_member=_staff_display_name(request.user),
                    note_type=request.POST.get('note_type', 'general'),
                    content=request.POST.get('content', ''),
                    next_steps=request.POST.get('next_steps', '') or None,
                    note_date=note_date or timezone.localdate(),
                )
                messages.success(request, f'Case note added successfully for {client.full_name}!')
                return redirect('admin:clients_client_change', object_id)
            except Exception as e:
                messages.error(request, f'Error adding case note: {str(e)}')
        
        # GET request - show quick add form
        context = {
            **self.admin_site.each_context(request),
            'title': f'Add Case Note - {client.full_name}',
            'client': client,
            'opts': self.model._meta,
            'has_view_permission': self.has_view_permission(request, client),
            'note_types': CaseNote.NOTE_TYPE_CHOICES,
        }
        return TemplateResponse(request, 'admin/clients/quick_add_case_note.html', context)
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('first_name', 'middle_name', 'last_name', 'dob', 'masked_ssn', 'phone', 'email', 'gender')
        }),
        ('Address', {
            'fields': ('address', 'city', 'state', 'zip_code')
        }),
        ('San Francisco Residency', {
            'fields': ('sf_resident', 'neighborhood', 'demographic_info', 'language', 'language_other')
        }),
        ('Education & Employment', {
            'fields': ('highest_degree', 'employment_status', 'training_interest')
        }),
        ('Referral & Notes', {
            'fields': ('referral_source', 'additional_notes')
        }),
        ('Case Notes', {
            'fields': ('case_notes_manage_link',),
            'description': 'Only the most recent notes are listed below. Use the link to edit dates on older notes.',
        }),
        ('Documents', {
            'fields': ('documents_checklist', 'documents_hub_link', 'resume', 'resume_download_link'),
            'description': 'Checklist only on this page — open Documents hub to upload or download (files load on demand).',
        }),
        ('Status & Tracking', {
            'fields': ('status', 'staff_name'),
            'description': 'Case manager is set automatically from your login when you create this client.',
        }),
        ('Program Completion', {
            'fields': ('program_completed_date',)
        }),
        ('Worker Portal', {
            'fields': ('worker_portal_summary',),
            'description': 'PitStop workers clock in/out on the iPad portal (time punches). No staff scheduling grid.',
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def has_resume(self, obj):
        if obj.resume:
            return format_html('<span style="color: green;">✓</span>')
        return format_html('<span style="color: red;">✗</span>')
    has_resume.short_description = 'Resume'
    
    def _client_present_doc_types(self, obj):
        present = set(obj.documents.exclude(file='').values_list('doc_type', flat=True))
        if obj.resume or 'resume' in present:
            present.add('resume')
        return present

    def _documents_by_type(self, obj):
        by_type = {}
        for doc in obj.documents.exclude(file='').order_by('-created_at'):
            if doc.doc_type not in by_type:
                by_type[doc.doc_type] = doc
        return by_type

    def _citybuild_checklist_context(self, obj):
        present = self._client_present_doc_types(obj)
        has_resume = 'resume' in present
        case_notes_count = obj.casenotes.count()
        docs_by_type = self._documents_by_type(obj)
        add_note_url = reverse('admin:clients_client_add_case_note', args=[obj.pk]) if obj.pk else None
        panels = []
        missing_items = []
        received_items = []
        on_file = 0
        total = 0
        for panel_title, items in CITYBUILD_CHECKLIST_PANELS:
            panel_items = []
            for code, label, source in items:
                total += 1
                present_item = citybuild_item_present(
                    code, source, present, has_resume, case_notes_count,
                )
                if present_item:
                    on_file += 1

                download_url = None
                file_label = ''
                if source == 'resume' and present_item:
                    if obj.resume:
                        download_url = reverse('client-resume-download', kwargs={'pk': obj.pk})
                        file_label = os.path.basename(obj.resume.name)
                    elif docs_by_type.get('resume'):
                        resume_doc = docs_by_type['resume']
                        download_url = reverse('document-download', kwargs={'pk': resume_doc.pk})
                        file_label = resume_doc.title
                elif source == 'document' and code and code in docs_by_type:
                    doc = docs_by_type[code]
                    download_url = reverse('document-download', kwargs={'pk': doc.pk})
                    file_label = doc.title

                item = {
                    'code': code,
                    'label': label,
                    'source': source,
                    'present': present_item,
                    'panel_title': panel_title,
                    'case_notes_count': case_notes_count if source == 'casenotes' else 0,
                    'download_url': download_url,
                    'file_label': file_label,
                    'add_note_url': add_note_url if source == 'casenotes' else None,
                }
                panel_items.append(item)
                if present_item:
                    received_items.append(item)
                else:
                    missing_items.append(item)
            panels.append({'title': panel_title, 'items': panel_items})
        progress_percent = round((on_file / total) * 100) if total else 0
        return {
            'panels': panels,
            'missing_items': missing_items,
            'received_items': received_items,
            'on_file_count': on_file,
            'total_count': total,
            'missing_count': total - on_file,
            'progress_percent': progress_percent,
        }

    def case_notes_manage_link(self, obj):
        if not obj or not obj.pk:
            return format_html('<span style="color:#999;">Save client first</span>')
        total = obj.casenotes.count()
        url = reverse('admin:clients_casenote_changelist') + f'?client__id__exact={obj.pk}'
        add_url = reverse('admin:clients_client_add_case_note', args=[obj.pk])
        return format_html(
            '<p style="margin:0 0 8px;">'
            '<a href="{}" class="button">View all {} case notes</a> '
            '<a href="{}" class="button" style="margin-left:8px;">+ Quick add note</a>'
            '</p>'
            '<p style="margin:0;color:#64748b;font-size:12px;">'
            'Edit <strong>Note date</strong> on any row for retroactive entry. '
            'Only the {} most recent notes appear in the section below.</p>',
            url,
            total,
            add_url,
            min(total, CASE_NOTE_INLINE_LIMIT),
        )
    case_notes_manage_link.short_description = 'All case notes'

    def documents_checklist(self, obj):
        if not obj or not obj.pk:
            return format_html('<span style="color:#999;">Save client first</span>')
        if is_citybuild_client(obj):
            ctx = self._citybuild_checklist_context(obj)
            html_parts = []
            for panel in ctx['panels']:
                html_parts.append(format_html(
                    '<tr><td colspan="3" style="padding:10px 10px 4px;font-size:11px;'
                    'text-transform:uppercase;letter-spacing:.04em;color:#64748b;font-weight:700;">{}</td></tr>',
                    panel['title'],
                ))
                for item in panel['items']:
                    if item['present']:
                        icon = '✓'
                        color = '#059669'
                        status = 'On file'
                    else:
                        icon = '○'
                        color = '#dc2626'
                        status = 'Missing'
                    html_parts.append(format_html(
                        '<tr><td style="padding:6px 10px;color:{};font-weight:700;">{}</td>'
                        '<td style="padding:6px 10px;"><strong>{}</strong></td>'
                        '<td style="padding:6px 10px;color:#64748b;">{}</td></tr>',
                        color, icon, item['label'], status,
                    ))
            summary = format_html(
                '<p style="margin:0 0 8px;font-size:13px;color:#334155;">'
                '<strong>City Build:</strong> {} / {} on file</p>',
                ctx['on_file_count'],
                ctx['total_count'],
            )
            if obj.citybuild_files_confirmed:
                summary = format_html(
                    '{}<p style="margin:0 0 8px;font-size:12px;color:#64748b;">'
                    'Confirmed by {}</p>',
                    summary,
                    obj.citybuild_files_confirmed_by or 'staff',
                )
            return format_html(
                '{}{}<table style="width:100%;max-width:520px;border-collapse:collapse;background:#f8fafc;'
                'border:1px solid #e2e8f0;border-radius:8px;">{}</table>',
                summary,
                '',
                format_html_join('', '{}', ((part,) for part in html_parts)),
            )
        present = self._client_present_doc_types(obj)
        rows = []
        for code, label in CLIENT_DOC_CHECKLIST:
            if code in present:
                icon = format_html('<span style="color:#059669;font-weight:700;">✓</span>')
                status = 'On file'
            else:
                icon = format_html('<span style="color:#dc2626;font-weight:700;">○</span>')
                status = 'Missing'
            rows.append((icon, label, status))
        table_rows = format_html_join(
            '',
            '<tr><td style="padding:6px 10px;">{}</td>'
            '<td style="padding:6px 10px;"><strong>{}</strong></td>'
            '<td style="padding:6px 10px;color:#64748b;">{}</td></tr>',
            rows,
        )
        return format_html(
            '<table style="width:100%;max-width:420px;border-collapse:collapse;background:#f8fafc;'
            'border:1px solid #e2e8f0;border-radius:8px;">{}</table>',
            table_rows,
        )
    documents_checklist.short_description = 'Document checklist'

    def documents_hub_link(self, obj):
        if not obj or not obj.pk:
            return '—'
        url = reverse('admin:clients_client_documents', args=[obj.pk])
        if is_citybuild_client(obj):
            ctx = self._citybuild_checklist_context(obj)
            label = 'City Build files hub'
            count_label = f'{ctx["on_file_count"]} / {ctx["total_count"]} checklist items'
        else:
            label = 'Open documents hub'
            file_count = obj.documents.exclude(file='').count() + (1 if obj.resume else 0)
            count_label = f'{file_count} on file'
        return format_html(
            '<a href="{}" class="button" style="padding:10px 16px;">📁 {} ({})</a>'
            '<p style="margin:8px 0 0;color:#64748b;font-size:12px;">'
            'Upload and download files there — nothing is pulled from Azure until you click download.</p>',
            url,
            label,
            count_label,
        )
    documents_hub_link.short_description = 'Manage files'

    def citybuild_files_summary(self, obj):
        if not obj or not obj.pk or not is_citybuild_client(obj):
            return '—'
        packet = citybuild_packet_for_client(obj)
        detail = (
            f'{packet["missing_count"]} missing — use the hub below for the full panel checklist.'
            if packet['missing_count']
            else 'Packet complete — use the hub below to review files or optional sign-off.'
        )
        confirmed = ''
        if obj.citybuild_files_confirmed:
            confirmed = format_html(
                '<br><span style="color:#64748b;">Signed off by {}</span>',
                obj.citybuild_files_confirmed_by or 'staff',
            )
        return format_html(
            '<p style="margin:0;line-height:1.5;color:#334155;">'
            '<strong>{} / {} on file</strong><br>'
            '<span style="color:#64748b;">{}</span>{}'
            '</p>',
            packet['on_file'],
            packet['total'],
            detail,
            confirmed,
        )
    citybuild_files_summary.short_description = 'Checklist summary'

    def resume_download_link(self, obj):
        if not obj or not obj.resume:
            return format_html('<span style="color:#999;">No resume on file</span>')
        filename = obj.resume.name.split('/')[-1]
        download_url = reverse('client-resume-download', kwargs={'pk': obj.pk})
        return format_html(
            '<a href="{}" target="_blank">📥 Download resume ({})</a>',
            download_url,
            filename,
        )
    resume_download_link.short_description = 'Resume file'

    def client_documents_view(self, request, object_id):
        """Separate page for document checklist, list, upload — no blob checks until download."""
        from django.shortcuts import get_object_or_404, redirect
        from django.template.response import TemplateResponse

        client = get_object_or_404(Client, pk=object_id)
        staff_name = _staff_display_name(request.user)
        force_checklist = request.GET.get('citybuild_checklist') == '1'
        show_citybuild_checklist = is_citybuild_client(client) or force_checklist
        docs_url = reverse('admin:clients_client_documents', args=[object_id])
        if force_checklist:
            docs_url = f'{docs_url}?citybuild_checklist=1'

        if request.method == 'POST':
            if request.POST.get('action') == 'save_confirmation' and show_citybuild_checklist:
                confirmed = request.POST.get('citybuild_confirmed') == '1'
                client.citybuild_files_confirmed = confirmed
                if confirmed:
                    client.citybuild_files_confirmed_by = staff_name
                    client.citybuild_files_confirmed_at = timezone.now()
                else:
                    client.citybuild_files_confirmed_by = ''
                    client.citybuild_files_confirmed_at = None
                client.save(update_fields=[
                    'citybuild_files_confirmed',
                    'citybuild_files_confirmed_by',
                    'citybuild_files_confirmed_at',
                    'updated_at',
                ])
                if confirmed:
                    messages.success(request, 'City Build file packet sign-off saved.')
                else:
                    messages.info(request, 'City Build sign-off cleared.')
                return redirect(docs_url)

            if request.POST.get('action') == 'upload_resume' and show_citybuild_checklist:
                resume_file = request.FILES.get('resume')
                if resume_file:
                    client.resume = resume_file
                    client.save(update_fields=['resume', 'updated_at'])
                    messages.success(request, f'Resume uploaded for {client.full_name}.')
                else:
                    messages.error(request, 'Choose a resume file to upload.')
                return redirect(docs_url)

            if request.POST.get('action') == 'upload_checklist_item' and show_citybuild_checklist:
                upload_file = request.FILES.get('file')
                checklist_source = request.POST.get('checklist_source', 'document')
                doc_type = (request.POST.get('doc_type') or '').strip()
                if not upload_file:
                    messages.error(request, 'Choose a file to upload.')
                    return redirect(docs_url)
                try:
                    if checklist_source == 'resume':
                        client.resume = upload_file
                        client.save(update_fields=['resume', 'updated_at'])
                        messages.success(request, 'Resume received — checklist updated.')
                    elif checklist_source == 'casenotes':
                        messages.info(request, 'Use “Add case note” on that tile to complete this item.')
                    elif doc_type in CITYBUILD_CHECKLIST_DOC_TYPES:
                        label = checklist_label_for_doc_type(doc_type)
                        Document.objects.create(
                            client=client,
                            title=label,
                            doc_type=doc_type,
                            file=upload_file,
                            uploaded_by=staff_name,
                        )
                        messages.success(request, f'{label} received — checklist updated.')
                    else:
                        messages.error(request, 'Unknown checklist item.')
                except Exception as exc:
                    messages.error(request, f'Upload failed: {exc}')
                return redirect(docs_url)

            upload_file = request.FILES.get('file')
            if upload_file:
                try:
                    Document.objects.create(
                        client=client,
                        title=(request.POST.get('title') or upload_file.name).strip()[:255],
                        doc_type=request.POST.get('doc_type') or 'other',
                        file=upload_file,
                        uploaded_by=staff_name,
                    )
                    messages.success(request, f'Uploaded {upload_file.name} for {client.full_name}.')
                except Exception as exc:
                    messages.error(request, f'Upload failed: {exc}')
            return redirect(docs_url)

        document_rows = []
        for doc in client.documents.exclude(file='').order_by('-created_at'):
            document_rows.append({
                'doc': doc,
                'download_url': reverse('document-download', kwargs={'pk': doc.pk}),
            })

        base_context = {
            **self.admin_site.each_context(request),
            'client': client,
            'document_rows': document_rows,
            'opts': self.model._meta,
            'resume_download_url': reverse('client-resume-download', kwargs={'pk': client.pk}) if client.resume else None,
            'back_url': reverse('admin:clients_client_change', args=[client.pk]),
        }

        if show_citybuild_checklist:
            ctx = self._citybuild_checklist_context(client)
            context = {
                **base_context,
                'title': f'City Build files — {client.full_name}',
                'panels': ctx['panels'],
                'missing_items': ctx['missing_items'],
                'received_items': ctx['received_items'],
                'on_file_count': ctx['on_file_count'],
                'total_count': ctx['total_count'],
                'missing_count': ctx['missing_count'],
                'progress_percent': ctx['progress_percent'],
            }
            return TemplateResponse(request, 'admin/clients/citybuild_client_documents.html', context)

        present = self._client_present_doc_types(client)
        checklist = [
            {'code': code, 'label': label, 'present': code in present}
            for code, label in CLIENT_DOC_CHECKLIST
        ]
        context = {
            **base_context,
            'title': f'Documents — {client.full_name}',
            'checklist': checklist,
            'doc_type_choices': Document.DOC_TYPE_CHOICES,
        }
        return TemplateResponse(request, 'admin/clients/client_documents.html', context)
    
    def case_notes_count(self, obj):
        # Uses queryset annotation to avoid per-row COUNT queries on changelist.
        count = getattr(obj, 'case_notes_total', None)
        if count is None:
            count = obj.casenotes.count()
        if count > 0:
            url = reverse('admin:clients_casenote_changelist') + f'?client__id__exact={obj.id}'
            return format_html('<a href="{}">{} notes</a>', url, count)
        return '0 notes'
    case_notes_count.short_description = 'Case Notes'

    def worker_portal_summary(self, obj):
        account = getattr(obj, 'worker_account', None)
        if not account:
            return format_html(
                '<div style="padding: 10px; background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px;">'
                '<strong>No worker portal account yet.</strong><br>'
                '<span>Use the list action "Create worker accounts" for PitStop workers.</span>'
                '</div>'
            )

        hours = _weekly_hours_for_worker(account)
        account_url = reverse('admin:clients_workeraccount_change', args=[account.pk])
        punches_url = (
            reverse('admin:clients_workertimepunch_changelist')
            + f'?worker_account__id__exact={account.pk}'
        )
        return format_html(
            '<div style="padding: 10px; background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; line-height: 1.5;">'
            '<strong>Portal:</strong> {}<br>'
            '<strong>Clocked this week:</strong> {}<br>'
            '<a href="{}">Open worker account</a> · '
            '<a href="{}">View time punches</a>'
            '</div>',
            'On' if account.is_active else 'Off',
            _format_hours(hours),
            account_url,
            punches_url,
        )

    worker_portal_summary.short_description = 'Worker portal summary'
    
    def masked_ssn(self, obj):
        """Show masked SSN (only last 4 digits) for non-superusers"""
        if not obj.ssn:
            return format_html('<span style="color: gray;">Not provided</span>')
        
        # Get request from threadlocal or check if we're in a superuser context
        from django.contrib.admin.views.main import ChangeList
        request = getattr(self, '_current_request', None)
        
        # Superusers can see full SSN
        if request and request.user.is_superuser:
            return obj.ssn
        
        # Mask SSN for regular users - show only last 4 digits
        if len(obj.ssn) >= 4:
            return f"XXX-XX-{obj.ssn[-4:]}"
        return "XXX-XX-XXXX"
    
    masked_ssn.short_description = 'SSN'
    
    def get_readonly_fields(self, request, obj=None):
        """Store request for later use and configure readonly fields"""
        self._current_request = request
        readonly = list(super().get_readonly_fields(request, obj))
        # masked_ssn is always readonly since it's a display method
        return readonly
    
    def get_fieldsets(self, request, obj=None):
        """Superusers edit raw SSN; never mutate class-level fieldsets."""
        self._current_request = request
        fieldsets = list(super().get_fieldsets(request, obj))
        if obj and is_citybuild_client(obj):
            fieldsets = [
                (
                    'City Build Files',
                    {
                        'fields': ('citybuild_files_summary', 'documents_hub_link'),
                        'description': (
                            'Checklist, uploads, resume, and sign-off live in the City Build files hub — '
                            'not on this page. Nothing is pulled from Azure until you download.'
                        ),
                    },
                )
                if title == 'Documents'
                else (title, options)
                for title, options in fieldsets
            ]
        if obj and request.user.is_superuser:
            title, options = fieldsets[0]
            personal = list(options['fields'])
            if 'masked_ssn' in personal and 'ssn' not in personal:
                personal = [
                    'ssn' if field == 'masked_ssn' else field
                    for field in personal
                ]
                fieldsets[0] = (title, {**options, 'fields': tuple(personal)})
        return fieldsets

    def get_fields(self, request, obj=None):
        self._current_request = request
        return super().get_fields(request, obj)
    
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(case_notes_total=Count('casenotes'))
    
    actions = [
        'mark_active',
        'mark_completed',
        'create_worker_accounts',
        'text_missing_documents',
        'export_to_csv',
        'export_program_report',
        'export_client_profiles_pdf',
    ]

    REQUIRED_DOC_TYPES_FOR_TEXT = ('resume', 'id', 'consent', 'intake')
    
    def create_worker_accounts(self, request, queryset):
        """Create worker portal accounts for selected PitStop clients"""
        created = 0
        skipped = 0
        errors = []
        
        for client in queryset:
            # Check if already has account
            if hasattr(client, 'worker_account'):
                skipped += 1
                continue
            
            # Check if phone exists
            if not client.phone:
                errors.append(f'{client.full_name}: No phone number')
                continue
            normalized_phone = normalize_login_phone(client.phone)
            if len(normalized_phone) < 10:
                errors.append(
                    f'{client.full_name}: Invalid phone "{client.phone}". '
                    'Needs a valid 10-digit number for worker login.'
                )
                continue
            
            try:
                pin = default_worker_pin_from_phone(normalized_phone)

                account = WorkerAccount(
                    client=client,
                    phone=normalized_phone,
                    is_active=True,
                    worker_status=WorkerAccount.STATUS_ACTIVE,
                    created_by=request.user.username,
                )
                account.set_pin(pin)
                account.save()
                created += 1
            except Exception as e:
                errors.append(f'{client.full_name}: {str(e)}')
        
        # Show results
        if created:
            self.message_user(request, f'✓ Created {created} worker account(s). PIN = last 4 digits of phone.', messages.SUCCESS)
        if skipped:
            self.message_user(request, f'⚠ Skipped {skipped} client(s) - already have accounts.', messages.WARNING)
        if errors:
            self.message_user(request, f'✗ Errors: {", ".join(errors)}', messages.ERROR)
    
    create_worker_accounts.short_description = "🏢 Create worker portal accounts (PIN = last 4 of phone)"

    def _missing_doc_types_for_client(self, client):
        present = set(
            client.documents.exclude(file='').values_list('doc_type', flat=True)
        )
        if client.resume:
            present.add('resume')
        return [doc for doc in self.REQUIRED_DOC_TYPES_FOR_TEXT if doc not in present]

    @admin.action(description='Text selected clients about missing documents')
    def text_missing_documents(self, request, queryset):
        from .notifications import send_text_message
        from .models_extensions import ClientTextMessage

        if not getattr(settings, 'AZURE_COMMUNICATION_CONNECTION_STRING', ''):
            self.message_user(
                request,
                'SMS not configured: missing AZURE_COMMUNICATION_CONNECTION_STRING in app settings.',
                level=messages.ERROR,
            )
            return
        if not getattr(settings, 'AZURE_COMMUNICATION_SMS_FROM', ''):
            self.message_user(
                request,
                'SMS not configured: missing AZURE_COMMUNICATION_SMS_FROM in app settings.',
                level=messages.ERROR,
            )
            return

        label_by_code = dict(Document.DOC_TYPE_CHOICES)
        sent = 0
        skipped = 0
        failed = 0
        email_backup_sent = 0
        email_backup_failed = 0
        reason_counts = {}

        for client in queryset.prefetch_related('documents'):
            missing_codes = self._missing_doc_types_for_client(client)
            if not missing_codes:
                skipped += 1
                continue
            missing_labels = [label_by_code.get(code, code) for code in missing_codes]
            docs_text = ', '.join(missing_labels)
            first_name = (client.first_name or client.full_name or 'there').strip()
            body = (
                f"Hi {first_name}, Mission Hiring Hall reminder: "
                f"we are still missing your documents: {docs_text}. "
                "Please upload or bring them in as soon as possible. Thank you."
            )
            dedupe_key = f'client:{client.pk}:missing-docs:{"-".join(sorted(missing_codes))}'
            log, attempted = send_text_message(
                client=client,
                body=body[:480],
                purpose=ClientTextMessage.PURPOSE_GENERAL,
                dedupe_key=dedupe_key,
                require_enabled_flag=False,
            )
            if not attempted:
                skipped += 1
            elif log.status == ClientTextMessage.STATUS_SENT:
                sent += 1
            else:
                failed += 1
                reason = (log.error_message or 'Unknown send error')[:80]
                reason_counts[reason] = reason_counts.get(reason, 0) + 1

            if getattr(settings, 'SMS_FORCE_EMAIL_BACKUP', True):
                email = (client.email or '').strip()
                if email:
                    try:
                        send_mail(
                            subject='Mission Hiring Hall: Missing documents reminder',
                            message=body[:480],
                            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@missionhiringhall.org'),
                            recipient_list=[email],
                            fail_silently=False,
                        )
                        email_backup_sent += 1
                    except Exception as exc:
                        email_backup_failed += 1
                        reason = f'Email backup failed: {exc}'
                        reason_counts[reason] = reason_counts.get(reason, 0) + 1

        level = messages.SUCCESS if failed == 0 else messages.WARNING
        reason_text = ''
        if reason_counts:
            top_reasons = ', '.join(f'{reason} ({count})' for reason, count in list(reason_counts.items())[:3])
            reason_text = f' Top failures: {top_reasons}.'
        self.message_user(
            request,
            (
                f'Missing-document texts queued: {sent}. Skipped: {skipped}. Failed: {failed}. '
                f'Email backup sent: {email_backup_sent}. Email backup failed: {email_backup_failed}.{reason_text}'
            ),
            level=level,
        )
    
    def mark_active(self, request, queryset):
        updated = queryset.update(status='active')
        self.message_user(request, f'{updated} clients marked as active.')
    mark_active.short_description = "Mark selected clients as active"
    
    def mark_completed(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(status='completed', program_completed_date=timezone.now().date())
        self.message_user(request, f'{updated} clients marked as completed with today\'s date.')
    mark_completed.short_description = "Mark selected clients as completed"
    
    def export_program_report(self, request, queryset):
        """Export program completion report"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="program_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Client Name', 'Phone', 'Email', 'Program', 'Status', 'Program Completed Date', 'Created Date'
        ])
        
        for client in queryset.select_related():
            writer.writerow([
                client.full_name,
                client.phone,
                client.email or '',
                client.get_training_interest_display(),
                client.get_status_display(),
                client.program_completed_date.strftime('%Y-%m-%d') if client.program_completed_date else '',
                client.created_at.strftime('%Y-%m-%d')
            ])
        
        return response
    export_program_report.short_description = "Export program completion report"
    
    def export_client_profiles_pdf(self, request, queryset):
        """Export client profiles as PDF documents - DISABLED (WeasyPrint removed)"""
        self.message_user(request, 'PDF generation is not available. WeasyPrint has been removed from the project.', level='error')
        return
    
    export_client_profiles_pdf.short_description = "Export client profiles as PDF (disabled)"

    # --- Safe delete handling ---
    def response_delete(self, request, obj_display, obj_id):
        """Redirect to the admin index after successful delete to avoid heavy related lookups."""
        messages.success(request, f"Deleted {obj_display} successfully.")
        return redirect('admin:index')

    def delete_view(self, request, object_id, extra_context=None):
        """Wrap delete view to handle unexpected errors gracefully and redirect to admin index."""
        try:
            return super().delete_view(request, object_id, extra_context=extra_context)
        except Exception as exc:  # Guard against unexpected cascade/introspection errors
            messages.error(request, f"Delete failed due to: {exc}")
            return redirect('admin:index')


@admin.register(CityBuildFileChecklist)
class CityBuildFileChecklistAdmin(admin.ModelAdmin):
    """
    Sidebar home for City Build file packets — changelist only, hub for detail.
    Add → upload a new Document (pick Academy doc type on the form).
    """

    list_display = [
        'open_files_hub',
        'training_interest',
        'staff_name',
        'status',
        'citybuild_on_file_display',
        'citybuild_missing_display',
        'citybuild_confirmed_display',
    ]
    list_filter = ['training_interest', 'status', 'staff_name', 'citybuild_files_confirmed']
    search_fields = ['first_name', 'last_name', 'phone', 'staff_name', 'email']
    list_display_links = ('open_files_hub',)
    ordering = ['last_name', 'first_name', 'id']
    list_per_page = 25

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .filter(
                Q(training_interest__in=CITYBUILD_PROGRAMS) |
                Q(training_interest='capsa')
            )
            .annotate(casenotes_count=Count('casenotes'))
            .prefetch_related('documents')
        )

    def has_add_permission(self, request):
        return request.user.has_perm('clients.add_document')

    def add_view(self, request, form_url='', extra_context=None):
        return redirect(reverse('admin:clients_document_add'))

    def change_view(self, request, object_id, form_url='', extra_context=None):
        url = reverse('admin:clients_client_documents', args=[object_id])
        return redirect(f'{url}?citybuild_checklist=1')

    def open_files_hub(self, obj):
        url = reverse('admin:clients_client_documents', args=[obj.pk])
        url = f'{url}?citybuild_checklist=1'
        return format_html('<a href="{}"><strong>{}</strong></a>', url, obj.full_name)
    open_files_hub.short_description = 'Client'

    def citybuild_on_file_display(self, obj):
        packet = citybuild_packet_for_client(obj)
        return f'{packet["on_file"]} / {packet["total"]}'
    citybuild_on_file_display.short_description = 'On file'

    def citybuild_missing_display(self, obj):
        packet = citybuild_packet_for_client(obj)
        if not packet['missing_count']:
            return format_html('<span style="color:#059669;font-weight:600;">Complete</span>')
        return str(packet['missing_count'])
    citybuild_missing_display.short_description = 'Missing'

    def citybuild_confirmed_display(self, obj):
        if obj.citybuild_files_confirmed:
            return format_html('<span style="color:#059669;">Yes</span>')
        return '—'
    citybuild_confirmed_display.short_description = 'Signed off'


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['client', 'title', 'doc_type', 'file_size_mb', 'uploaded_by', 'created_at', 'download_link']
    list_filter = ['doc_type', 'created_at', 'uploaded_by']
    search_fields = ['client__first_name', 'client__last_name', 'title', 'uploaded_by']
    readonly_fields = [
        'created_at',
        'updated_at',
        'file_size',
        'content_type',
        'uploaded_by',
        'file_preview',
        'blob_path_info',
    ]
    date_hierarchy = 'created_at'
    actions = ['safe_delete_selected', 'verify_blob_exists', 'list_all_blobs', 'check_storage_config']
    
    fieldsets = (
        ('Document Information', {
            'fields': ('client', 'title', 'doc_type', 'file', 'file_preview', 'blob_path_info'),
            'description': 'Upload a new file or preview/download existing files below.'
        }),
        ('Metadata', {
            'fields': ('file_size', 'content_type', 'uploaded_by', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def file_size_mb(self, obj):
        if obj.file_size:
            return f"{obj.file_size_mb} MB"
        return "Unknown"
    file_size_mb.short_description = 'File Size'
    
    def file_preview(self, obj):
        """Download link only — blob verification runs when staff clicks download."""
        if not obj.file:
            return format_html('<span style="color: #999;">No file uploaded</span>')

        filename = obj.file.name.split('/')[-1]
        download_url = reverse('document-download', kwargs={'pk': obj.pk})
        return format_html(
            '<div style="margin-top: 10px;">'
            '<strong>{}</strong><br>'
            '<a href="{}" target="_blank" style="display: inline-block; margin-top: 10px; padding: 8px 16px; '
            'background: #1976d2; color: white; text-decoration: none; border-radius: 4px;">'
            '📥 Download document</a>'
            '</div>',
            filename,
            download_url,
        )
    file_preview.short_description = 'Download'
    
    def download_link(self, obj):
        """Quick download link for list view"""
        if not obj.file:
            return '-'
        download_url = reverse('document-download', kwargs={'pk': obj.pk})
        return format_html('<a href="{}" target="_blank">📥</a>', download_url)
    download_link.short_description = 'Download'
    
    def blob_path_info(self, obj):
        """Display blob path information for debugging"""
        if not obj.file:
            return format_html('<span style="color: #999;">No file uploaded</span>')
        
        blob_name = obj.file.name
        container = os.getenv('AZURE_CONTAINER', 'client-docs')
        
        info = f"<strong>Blob Name:</strong> {blob_name}<br>"
        info += f"<strong>Container:</strong> {container}<br>"
        info += f"<strong>Full Path:</strong> {container}/{blob_name}"
        
        return format_html(info)
    blob_path_info.short_description = 'Azure Blob Path'

    def save_model(self, request, obj, form, change):
        obj.uploaded_by = _staff_display_name(request.user)
        super().save_model(request, obj, form, change)

    def safe_delete_selected(self, request, queryset):
        """Bulk delete that swallows storage errors and continues."""
        deleted = 0
        for doc in queryset:
            try:
                doc.delete()
                deleted += 1
            except Exception as exc:
                messages.warning(request, f"Failed to delete blob for '{doc}': {exc}")
        messages.success(request, f"Deleted {deleted} document(s).")
    safe_delete_selected.short_description = "Safely delete selected documents"
    
    actions = ['safe_delete_selected', 'verify_blob_exists', 'list_all_blobs', 'check_storage_config']
    
    def verify_blob_exists(self, request, queryset):
        """Verify that selected documents exist in Azure Blob Storage"""
        from .storage import get_azure_container_client
        
        container_client = get_azure_container_client()
        if not container_client:
            messages.error(request, "Azure storage not configured")
            return
        
        verified = 0
        missing = 0
        errors = []
        
        for doc in queryset:
            if not doc.file:
                errors.append(f"{doc.title}: No file attached")
                missing += 1
                continue
            
            blob_name = doc.file.name
            try:
                # Check if blob exists
                blob_client = container_client.get_blob_client(blob_name)
                exists = blob_client.exists()
                
                if exists:
                    verified += 1
                    messages.success(request, f"✓ {doc.title}: Blob exists ({blob_name})")
                else:
                    missing += 1
                    # Try alternative path
                    alt_blob_name = blob_name.replace('documents/', 'resumes/', 1) if 'documents/' in blob_name else None
                    if alt_blob_name:
                        alt_blob_client = container_client.get_blob_client(alt_blob_name)
                        if alt_blob_client.exists():
                            messages.warning(request, f"⚠ {doc.title}: Found at alternative path ({alt_blob_name})")
                            verified += 1
                            missing -= 1
                        else:
                            errors.append(f"{doc.title}: Not found at {blob_name} or {alt_blob_name}")
                    else:
                        errors.append(f"{doc.title}: Not found at {blob_name}")
            except Exception as e:
                errors.append(f"{doc.title}: Error checking - {str(e)}")
                missing += 1
        
        if errors:
            for error in errors[:10]:  # Show first 10 errors
                messages.error(request, error)
            if len(errors) > 10:
                messages.warning(request, f"... and {len(errors) - 10} more errors")
        
        messages.info(request, f"Verified: {verified} found, {missing} missing")
    verify_blob_exists.short_description = "Verify blobs exist in Azure Storage"
    
    def list_all_blobs(self, request, queryset):
        """List all blobs in Azure container for comparison"""
        from .storage import get_azure_container_client
        
        container_client = get_azure_container_client()
        if not container_client:
            messages.error(request, "Azure storage not configured")
            return
        
        try:
            blobs = list(container_client.list_blobs())
            blob_names = [blob.name for blob in blobs]
            
            # Show in a message (limited to avoid overwhelming)
            if blob_names:
                messages.info(request, f"Found {len(blob_names)} blobs in Azure:")
                for name in blob_names[:20]:  # Show first 20
                    messages.info(request, f"  - {name}")
                if len(blob_names) > 20:
                    messages.info(request, f"  ... and {len(blob_names) - 20} more")
            else:
                messages.warning(request, "No blobs found in Azure container")
        except Exception as e:
            messages.error(request, f"Error listing blobs: {str(e)}")
    list_all_blobs.short_description = "List all blobs in Azure Storage"
    
    def check_storage_config(self, request, queryset):
        """Diagnostic: Check Azure storage configuration and environment variables"""
        from django.conf import settings
        
        # Check environment variables
        account_name = os.getenv('AZURE_ACCOUNT_NAME')
        account_key = os.getenv('AZURE_ACCOUNT_KEY')
        container = os.getenv('AZURE_CONTAINER', 'client-docs')
        
        # Check Django settings
        storage_backend = getattr(settings, 'DEFAULT_FILE_STORAGE', 'Not set')
        settings_module = os.getenv('DJANGO_SETTINGS_MODULE', 'Not set')
        
        messages.info(request, "=== Azure Storage Configuration ===")
        messages.info(request, f"Settings Module: {settings_module}")
        
        # Environment variables
        if account_name:
            messages.success(request, f"✓ AZURE_ACCOUNT_NAME: {account_name[:10]}... (configured)")
        else:
            messages.error(request, "✗ AZURE_ACCOUNT_NAME: NOT SET")
        
        if account_key:
            messages.success(request, f"✓ AZURE_ACCOUNT_KEY: {'*' * 20}... (configured)")
        else:
            messages.error(request, "✗ AZURE_ACCOUNT_KEY: NOT SET")
        
        messages.info(request, f"Container: {container}")
        messages.info(request, f"Storage Backend: {storage_backend}")
        
        # Test Azure connection
        if account_name and account_key:
            from .storage import get_azure_container_client
            container_client = get_azure_container_client()
            if container_client:
                try:
                    exists = container_client.exists()
                    if exists:
                        messages.success(request, f"✓ Azure container '{container}' exists and is accessible")
                        
                        # List some blobs
                        blobs = list(container_client.list_blobs(results_per_page=10))
                        messages.info(request, f"Found {len(blobs)} blobs (showing first 10):")
                        for blob in blobs:
                            messages.info(request, f"  - {blob.name} ({blob.size} bytes)")
                    else:
                        messages.error(request, f"✗ Azure container '{container}' does NOT exist")
                except Exception as e:
                    messages.error(request, f"✗ Error connecting to Azure: {str(e)}")
            else:
                messages.error(request, "✗ Failed to create Azure container client")
        else:
            messages.warning(request, "⚠ Azure credentials not configured - using local storage")
        
        # Check actual storage being used
        if 'AzurePrivateStorage' in str(storage_backend):
            messages.success(request, "✓ Using Azure Blob Storage")
        else:
            messages.warning(request, f"⚠ Using local storage: {storage_backend}")
        
        # Check document file paths
        if queryset.exists():
            messages.info(request, "\n=== Document File Paths ===")
            for doc in queryset[:5]:  # Show first 5
                if doc.file:
                    messages.info(request, f"  {doc.title}: {doc.file.name}")
    check_storage_config.short_description = "🔍 Check Storage Configuration & Environment"

@admin.register(PitStopApplication)
class PitStopApplicationAdmin(admin.ModelAdmin):
    list_display = ['client', 'position_applied_for', 'employment_desired', 'can_work_us', 'is_veteran', 'open_availability_status', 'created_at']
    list_filter = ['employment_desired', 'can_work_us', 'is_veteran', 'created_at']
    search_fields = ['client__first_name', 'client__last_name', 'position_applied_for']
    autocomplete_fields = ['client']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'updated_at']

    def open_availability_status(self, obj):
        schedule = obj.weekly_schedule or {}
        for _, times in schedule.items():
            if isinstance(times, list) and times:
                return format_html('<strong style="color:#15803d;">OPEN AVAILABILITY</strong>')
        return format_html('<strong style="color:#b91c1c;">NOT OPEN</strong>')
    open_availability_status.short_description = 'Open Availability'


# ========================================
# Worker Portal Admin Interfaces
# ========================================

@admin.register(WorkerAccount)
class WorkerAccountAdmin(admin.ModelAdmin):
    """Primary PitStop roster focused on clock in/out tracking."""
    list_display = [
        'client',
        'phone',
        'worker_status',
        'portal_access_display',
        'weekly_hours_check',
        'last_punch_display',
    ]
    list_filter = ['worker_status', 'is_active', 'created_at']
    search_fields = ['client__first_name', 'client__last_name', 'phone']
    autocomplete_fields = ['client']
    readonly_fields = [
        'phone',
        'pin_hash',
        'last_login',
        'login_attempts',
        'locked_until',
        'created_at',
        'weekly_hours_check',
        'total_hours_display',
        'last_punch_display',
        'related_records_links',
    ]
    inlines = []

    fieldsets = (
        ('Worker', {
            'fields': ('client', 'phone', 'worker_status', 'is_active'),
            'description': 'Portal access must be on for iPad login. PIN defaults to last 4 digits of phone.',
        }),
        ('Worker portal profile', {
            'fields': ('short_profile', 'long_term_career_goals'),
            'description': 'Worker-written profile content from the worker portal.',
        }),
        ('Hours + clock logs', {
            'fields': ('weekly_hours_check', 'total_hours_display', 'last_punch_display', 'related_records_links'),
        }),
        ('Notes (optional)', {
            'classes': ('collapse',),
            'fields': ('notes', 'created_by', 'created_at'),
        }),
        ('Login audit', {
            'classes': ('collapse',),
            'fields': ('last_login', 'login_attempts', 'locked_until', 'pin_hash'),
        }),
    )

    add_fieldsets = (
        (None, {
            'fields': ('client',),
            'description': (
                'Type name or phone to search — PitStop clients only. '
                'Portal access, phone, and PIN are set automatically when you save.'
            ),
        }),
    )

    actions = [
        'enable_portal_welcome',
        'disable_portal',
        'reset_pins',
        'unlock_accounts',
    ]

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return self.add_fieldsets
        return self.fieldsets

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return []
        return list(self.readonly_fields)

    def save_model(self, request, obj, form, change):
        if obj.client_id:
            normalized = normalize_login_phone(obj.client.phone)
            if normalized:
                obj.phone = normalized
            elif not obj.phone:
                obj.phone = normalize_login_phone(obj.client.phone) or (obj.client.phone or '')
        if not change:
            if not obj.pin_hash:
                obj.set_pin(default_worker_pin_from_phone(obj.phone))
            obj.created_by = _staff_display_name(request.user)
            obj.worker_status = WorkerAccount.STATUS_ACTIVE
            obj.is_active = True
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'client' and not request.path.endswith('/autocomplete/'):
            kwargs['queryset'] = (
                Client.objects.filter(training_interest='pit_stop')
                .select_related()
                .order_by('last_name', 'first_name', 'id')
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def portal_access_display(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green; font-weight: bold;">✓ On</span>')
        return format_html('<span style="color: #999;">Off</span>')
    portal_access_display.short_description = 'Portal'

    def current_week_hours(self, obj):
        return _format_hours(_weekly_hours_for_worker(obj))

    current_week_hours.short_description = 'Clocked this week'

    def weekly_hours_check(self, obj):
        hours = _weekly_hours_for_worker(obj)
        if hours > 40:
            return format_html(
                '<span style="color: #b91c1c; font-weight: bold;">{} - over 40 hrs</span>',
                _format_hours(hours),
            )
        return format_html('<span style="color: #166534;">{}</span>', _format_hours(hours))

    weekly_hours_check.short_description = 'Clocked this week'

    def total_hours_display(self, obj):
        return _format_hours(_total_hours_for_worker(obj))

    total_hours_display.short_description = 'Clocked total'

    def last_punch_display(self, obj):
        punch = _last_assignment_for_worker(obj)
        if not punch:
            return '—'
        url = reverse('admin:clients_workertimepunch_change', args=[punch.pk])
        site_name = punch.work_site.name if punch.work_site else 'Site not set'
        return format_html(
            '<a href="{}">{} · {}</a>',
            url,
            format_display_datetime(punch.clock_in_at),
            site_name,
        )

    last_punch_display.short_description = 'Last punch'

    def related_records_links(self, obj):
        if not obj or not obj.pk:
            return 'Save first to view related records.'
        punches_url = (
            reverse('admin:clients_workertimepunch_changelist')
            + f'?worker_account__id__exact={obj.pk}'
        )
        return format_html(
            '<a href="{}">View clock punches</a>',
            punches_url,
        )

    related_records_links.short_description = 'Related records'

    def enable_portal_welcome(self, request, queryset):
        """Turn portal on and send welcome emails."""
        from .notifications import send_worker_welcome_email

        approved = 0
        emailed = 0
        for account in queryset.filter(is_active=False):
            account.is_active = True
            account.worker_status = WorkerAccount.STATUS_ACTIVE
            account.save()
            approved += 1
            if send_worker_welcome_email(account):
                emailed += 1

        msg = f'{approved} account(s) enabled for portal.'
        if emailed:
            msg += f' {emailed} welcome email(s) sent.'
        if approved == 0:
            msg = 'No changes — selected accounts already had portal access on.'
        self.message_user(request, msg)
    enable_portal_welcome.short_description = 'Enable portal + welcome email'

    def disable_portal(self, request, queryset):
        updated = queryset.update(
            is_active=False,
            worker_status=WorkerAccount.STATUS_INACTIVE,
        )
        self.message_user(request, f'Portal login disabled for {updated} account(s).')
    disable_portal.short_description = 'Disable portal login'

    def reset_pins(self, request, queryset):
        """Reset PINs to last four digits of the phone number (numeric)."""
        for account in queryset:
            account.set_pin(default_worker_pin_from_phone(account.phone))
            account.login_attempts = 0
            account.locked_until = None
            account.save()
        self.message_user(request, f'PINs reset to last 4 digits of phone for {queryset.count()} account(s).')
    reset_pins.short_description = 'Reset PIN to phone last 4 digits'
    
    def unlock_accounts(self, request, queryset):
        """Unlock locked accounts"""
        updated = queryset.update(login_attempts=0, locked_until=None)
        self.message_user(request, f'{updated} account(s) unlocked.')
    unlock_accounts.short_description = 'Unlock selected accounts'


@admin.register(WorkSite)
class WorkSiteAdmin(admin.ModelAdmin):
    """PitStop work sites used for geofenced clock in/out."""

    list_display = [
        'name',
        'neighborhood',
        'site_type',
        'gps_status',
        'latitude',
        'longitude',
        'is_active',
    ]
    list_filter = ['is_active', 'site_type', 'neighborhood']
    search_fields = ['name', 'address', 'neighborhood', 'supervisor_name', 'supervisor_email']
    fieldsets = (
        (None, {
            'fields': (
                'name',
                'site_type',
                'address',
                'neighborhood',
                'is_active',
            ),
        }),
        ('Geofence GPS', {
            'fields': ('latitude', 'longitude'),
            'description': (
                'Set coordinates to the center of the PitStop (map pin at the curb/table). '
                'Workers are validated within ~200 yards of any active PitStop with coordinates.'
            ),
        }),
        ('Supervisor & shifts', {
            'classes': ('collapse',),
            'fields': (
                'supervisor_name',
                'supervisor_phone',
                'supervisor_email',
                'typical_start_time',
                'typical_end_time',
                'available_time_slots',
                'max_workers_per_shift',
            ),
        }),
    )

    def gps_status(self, obj):
        if obj.latitude is not None and obj.longitude is not None:
            return format_html('<span style="color: #15803d; font-weight: 700;">✓ GPS set</span>')
        return format_html('<span style="color: #b91c1c; font-weight: 700;">⚠ Missing GPS</span>')
    gps_status.short_description = 'Geofence'


@admin.register(ClientTextMessage)
class ClientTextMessageAdmin(admin.ModelAdmin):
    """Admin log for Azure SMS outreach and replies."""

    list_display = [
        'client',
        'direction',
        'purpose',
        'checkpoint_days',
        'to_phone',
        'status',
        'sent_at',
        'created_at',
    ]
    list_filter = ['direction', 'purpose', 'status', 'checkpoint_days', 'created_at', 'sent_at']
    search_fields = [
        'client__first_name',
        'client__last_name',
        'client__phone',
        'to_phone',
        'from_phone',
        'body',
        'provider_message_id',
    ]
    readonly_fields = [
        'client',
        'direction',
        'purpose',
        'checkpoint_days',
        'dedupe_key',
        'to_phone',
        'from_phone',
        'body',
        'status',
        'provider_message_id',
        'provider_response',
        'error_message',
        'sent_at',
        'received_at',
        'created_at',
        'updated_at',
    ]
    date_hierarchy = 'created_at'


@admin.register(WorkerTimePunch)
class WorkerTimePunchAdmin(admin.ModelAdmin):
    """Quick-glance clock log: compact columns, hidden GPS audit by default."""

    list_display = [
        'worker_account',
        'work_site',
        'clock_in_at',
        'clock_out_at',
        'hours_display',
        'location_reference',
    ]
    list_filter = [
        'work_site',
        'clock_in_at',
        'clock_in_geo_basic_ok',
        'clock_out_geo_basic_ok',
    ]
    search_fields = [
        'worker_account__client__first_name',
        'worker_account__client__last_name',
        'worker_account__phone',
        'work_site__name',
    ]
    autocomplete_fields = ['worker_account', 'work_site']
    date_hierarchy = 'clock_in_at'
    actions = ['export_pitstop_hours_csv']

    fieldsets = (
        ('Punch', {
            'fields': (
                'worker_account',
                'work_site',
                'clock_in_at',
                'clock_out_at',
                'hours_display',
            ),
        }),
        ('Location reference', {
            'fields': (
                'clock_in_location_label',
                'clock_in_map_preview',
                'clock_out_location_label',
                'clock_out_map_preview',
            ),
            'description': 'Map snapshots and labels are visual references only (no geofence validation).',
        }),
        ('Raw audit (advanced)', {
            'classes': ('collapse',),
            'fields': (
                'assignment',
                'clock_in_server_received_at',
                'clock_out_server_received_at',
                'clock_in_client_reported_at',
                'clock_out_client_reported_at',
                'clock_in_latitude',
                'clock_in_longitude',
                'clock_in_accuracy_meters',
                'clock_in_geo_status',
                'clock_in_geo_error',
                'clock_out_latitude',
                'clock_out_longitude',
                'clock_out_accuracy_meters',
                'clock_out_geo_status',
                'clock_out_geo_error',
            ),
            'description': 'Raw GPS payload kept for audits. Superusers can correct records here.',
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        # auto_now_add fields must be readonly or Django raises FieldError on the change form
        auto_fields = ['clock_in_server_received_at']
        previews = ['clock_in_map_preview', 'clock_out_map_preview']
        if request.user.is_superuser:
            return ['hours_display'] + previews + auto_fields
        return [f.name for f in WorkerTimePunch._meta.fields] + ['hours_display'] + previews

    def has_delete_permission(self, request, obj=None):
        return bool(request.user and request.user.is_superuser)

    def hours_display(self, obj):
        if not obj or not obj.clock_in_at or not obj.clock_out_at:
            return '—'
        seconds = max((obj.clock_out_at - obj.clock_in_at).total_seconds(), 0)
        return f'{seconds / 3600:.2f}'
    hours_display.short_description = 'Hours'

    def _map_preview(self, image_field):
        if not image_field:
            return '—'
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">'
            '<img src="{}" alt="Map snapshot" style="max-width:220px;border-radius:6px;border:1px solid #e2e8f0;" />'
            '</a>',
            image_field.url,
            image_field.url,
        )

    def clock_in_map_preview(self, obj):
        return self._map_preview(obj.clock_in_map_image if obj else None)
    clock_in_map_preview.short_description = 'Clock-in map'

    def clock_out_map_preview(self, obj):
        return self._map_preview(obj.clock_out_map_image if obj else None)
    clock_out_map_preview.short_description = 'Clock-out map'

    def location_reference(self, obj):
        if not obj:
            return '—'
        parts = []
        if obj.clock_in_location_label or obj.clock_in_map_image:
            label = obj.clock_in_location_label or 'Map saved'
            parts.append(f'In: {label}')
        if obj.clock_out_at and (obj.clock_out_location_label or obj.clock_out_map_image):
            label = obj.clock_out_location_label or 'Map saved'
            parts.append(f'Out: {label}')
        if not parts:
            return format_html('<span style="color:#64748b;">No location snapshot</span>')
        return format_html('<span style="color:#334155;">{}</span>', ' · '.join(parts)[:160])
    location_reference.short_description = 'Location'

    @admin.action(description='Export selected punches to PitStop Hours CSV')
    def export_pitstop_hours_csv(self, request, queryset):
        from .reports import write_pitstop_hours_csv

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = (
            f'attachment; filename="pitstop_hours_selection_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        )
        write_pitstop_hours_csv(
            response,
            queryset.select_related('worker_account__client', 'work_site').order_by('-clock_in_at'),
        )
        return response


@admin.register(WorkerDailyFeedback)
class WorkerDailyFeedbackAdmin(admin.ModelAdmin):
    list_display = ['worker_account', 'feedback_date', 'preview', 'updated_at']
    list_filter = ['feedback_date', 'updated_at']
    search_fields = [
        'worker_account__client__first_name',
        'worker_account__client__last_name',
        'feedback_text',
    ]
    autocomplete_fields = ['worker_account']
    readonly_fields = ['created_at', 'updated_at']

    def preview(self, obj):
        text = (obj.feedback_text or '').strip()
        return (text[:80] + '...') if len(text) > 80 else text
    preview.short_description = 'Feedback'

