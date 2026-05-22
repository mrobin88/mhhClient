from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.db.models import Count
from datetime import datetime, time, timedelta
import csv
import io
import logging
import os
from django.shortcuts import redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.utils import timezone
from .models import Client, CaseNote, Document, PitStopApplication, JobPlacement
from .models_extensions import (
    WorkSite,
    WorkAssignment,
    WorkerAccount,
    WorkerTimePunch,
    ServiceRequest,
    OpenShift,
    ShiftCoverInterest,
    WorkerShiftProof,
    WorkerPortalNote,
    WorkerTimeOffRequest,
    ClientTextMessage,
)
from .phone_utils import default_worker_pin_from_phone, normalize_login_phone


def _current_week_bounds():
    today = timezone.localdate()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=7)
    start_dt = timezone.make_aware(datetime.combine(week_start, time.min))
    end_dt = timezone.make_aware(datetime.combine(week_end, time.min))
    return start_dt, end_dt


def _format_hours(hours):
    return f'{hours:.2f} hrs'


def _assignment_duration_hours(assignment):
    start_dt = datetime.combine(assignment.assignment_date, assignment.start_time)
    end_dt = datetime.combine(assignment.assignment_date, assignment.end_time)
    if end_dt <= start_dt:
        end_dt += timedelta(days=1)
    seconds = max((end_dt - start_dt).total_seconds(), 0)
    return seconds / 3600


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


class WorkAssignmentInline(admin.TabularInline):
    """Schedule rows directly on the client profile."""

    model = WorkAssignment
    fk_name = 'client'
    extra = 0
    fields = [
        'work_site',
        'assignment_date',
        'start_time',
        'end_time',
        'status',
        'confirmed_by_client',
    ]
    ordering = ['-assignment_date', 'start_time']
    autocomplete_fields = []


class CaseNoteInline(admin.TabularInline):
    """Inline admin for displaying case notes as a timestamped list on Client admin page"""
    model = CaseNote
    extra = 0  # Don't show empty forms by default - use "Add another Case Note" button
    readonly_fields = ['formatted_timestamp', 'overdue_indicator']
    fields = ['formatted_timestamp', 'overdue_indicator', 'staff_member', 'note_type', 'content', 'next_steps', 'follow_up_date']
    ordering = ['-created_at']  # Newest first
    can_delete = True
    verbose_name = 'Case Note'
    verbose_name_plural = 'Case Notes Timeline (Each row = ONE separate entry)'
    
    def get_readonly_fields(self, request, obj=None):
        """Show formatted timestamp only for existing notes"""
        readonly = list(super().get_readonly_fields(request, obj))
        if obj and obj.pk:  # Existing case note
            readonly.append('formatted_timestamp')
            readonly.append('overdue_indicator')
        return readonly
    
    class Media:
        css = {
            'all': ()
        }
        js = ()
    
    def overdue_indicator(self, obj):
        """Show overdue follow-up indicator"""
        if not obj or not obj.pk:
            return format_html('<em style="color: #999;">New</em>')
        
        if obj.is_overdue_followup:
            return format_html(
                '<span style="background: #ef4444; color: white; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;">⚠️ OVERDUE</span>'
            )
        elif obj.follow_up_date:
            from datetime import date
            days_until = (obj.follow_up_date - date.today()).days
            if days_until <= 3:
                return format_html(
                    '<span style="background: #f59e0b; color: white; padding: 4px 8px; border-radius: 4px; font-size: 11px;">Due in {} day{}</span>',
                    days_until,
                    's' if days_until != 1 else ''
                )
        return format_html('<span style="color: #10b981;">✓</span>')
    overdue_indicator.short_description = 'Status'
    
    def formatted_timestamp(self, obj):
        """Display formatted timestamp with relative time"""
        if not obj or not obj.pk or not obj.created_at:
            return format_html('<em style="color: #999;">New note</em>')
        
        # Format: "Jan 15, 2025 at 2:30 PM"
        formatted = obj.created_at.strftime('%b %d, %Y at %I:%M %p')
        
        # Add relative time
        now = timezone.now()
        if obj.created_at.tzinfo:
            diff = now - obj.created_at
        else:
            # Handle naive datetime
            diff = timezone.make_aware(now) - timezone.make_aware(obj.created_at)
        
        if diff.days > 0:
            relative = f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds >= 3600:
            hours = diff.seconds // 3600
            relative = f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.seconds >= 60:
            minutes = diff.seconds // 60
            relative = f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            relative = "just now"
        
        return format_html(
            '<div style="line-height: 1.4;">'
            '<strong style="color: #1976d2; display: block; font-size: 13px;">{}</strong>'
            '<small style="color: #64748b; font-size: 11px;">{}</small>'
            '</div>',
            formatted,
            relative
        )
    formatted_timestamp.short_description = 'Timestamp'
    
    def has_add_permission(self, request, obj=None):
        """Allow adding new case notes"""
        return True
    
    def has_change_permission(self, request, obj=None):
        """Allow editing case notes"""
        return True


class DocumentInline(admin.TabularInline):
    """Inline admin for uploading/reviewing supporting documents on the Client page."""
    model = Document
    extra = 0
    verbose_name = 'Document'
    verbose_name_plural = 'Supporting Documents (stored in Azure Blob Storage)'
    fields = ['doc_type', 'title', 'file', 'created_at', 'inline_download']
    readonly_fields = ['created_at', 'inline_download']
    ordering = ['-created_at']

    def inline_download(self, obj):
        if not obj or not obj.pk or not obj.file:
            return format_html('<span style="color: #999;">-</span>')
        url = obj.download_url
        if url:
            return format_html('<a href="{}" target="_blank">📥 Download</a>', url)
        return format_html('<span style="color: #f44336;" title="File missing from Azure">⚠️ Missing</span>')
    inline_download.short_description = 'Download'


@admin.register(CaseNote)
class CaseNoteAdmin(admin.ModelAdmin):
    list_display = ['formatted_date', 'client', 'note_type', 'content_preview', 'follow_up_date', 'is_overdue']
    list_filter = ['note_type', 'staff_member', 'created_at', 'follow_up_date']
    search_fields = ['client__first_name', 'client__last_name', 'content', 'staff_member']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'updated_at']
    list_per_page = 50
    
    fieldsets = (
        ('Client Information', {
            'fields': ('client', 'staff_member')
        }),
        ('Note Details', {
            'fields': ('note_type', 'content', 'next_steps'),
            'description': '⚠️ IMPORTANT: Each case note should be ONE entry. If you have multiple dated entries (e.g., "09/02/2025...", "09/09/2025..."), create SEPARATE case notes for each date.'
        }),
        ('Follow-up', {
            'fields': ('follow_up_date',),
            'description': 'Set a follow-up date to receive email alerts when it\'s due or overdue.'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def is_overdue(self, obj):
        if obj.is_overdue_followup:
            return format_html('<span style="color: red; font-weight: bold;">⚠️ OVERDUE</span>')
        elif obj.follow_up_date:
            from datetime import date
            days_until = (obj.follow_up_date - date.today()).days
            if days_until <= 3:
                return format_html('<span style="color: orange;">Due in {} day{}</span>', days_until, 's' if days_until != 1 else '')
        return format_html('<span style="color: green;">✓ On Track</span>')
    is_overdue.short_description = 'Follow-up Status'
    
    actions = ['export_to_csv', 'send_followup_alerts_action']
    
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
            'Follow-up Date',
            'Follow-up Status',
            'Created At',
            'Updated At'
        ])
        
        # Write data rows
        for note in queryset.select_related('client'):
            # Calculate follow-up status
            followup_status = ''
            if note.follow_up_date:
                from datetime import date
                days_diff = (note.follow_up_date - date.today()).days
                if days_diff < 0:
                    followup_status = f'OVERDUE ({abs(days_diff)} days)'
                elif days_diff == 0:
                    followup_status = 'Due Today'
                else:
                    followup_status = f'Due in {days_diff} day{"s" if days_diff > 1 else ""}'
            else:
                followup_status = 'No follow-up'
            
            writer.writerow([
                note.id,
                note.client.full_name,
                note.client.phone,
                note.client.email or '',
                note.get_note_type_display(),
                note.staff_member,
                note.content,
                note.next_steps or '',
                note.follow_up_date.strftime('%Y-%m-%d') if note.follow_up_date else '',
                followup_status,
                note.created_at.strftime('%Y-%m-%d %H:%M:%S') if note.created_at else '',
                note.updated_at.strftime('%Y-%m-%d %H:%M:%S') if note.updated_at else '',
            ])
        
        self.message_user(request, f'✅ Exported {queryset.count()} case note(s) to CSV')
        return response
    
    export_to_csv.short_description = "Download selected case notes in CSV"
    
    def formatted_date(self, obj):
        """Display formatted date"""
        if obj.created_at:
            return obj.created_at.strftime('%Y-%m-%d')
        return '-'
    formatted_date.short_description = 'Date'
    formatted_date.admin_order_field = 'created_at'
    
    def content_preview(self, obj):
        """Display content preview (first 100 chars)"""
        if obj.content:
            preview = obj.content[:100]
            if len(obj.content) > 100:
                preview += '...'
            return preview
        return '-'
    content_preview.short_description = 'Note'
    
    def send_followup_alerts_action(self, request, queryset):
        """Admin action to send follow-up alerts for selected case notes"""
        from clients.notifications import send_followup_alert
        from users.models import StaffUser
        
        sent = 0
        errors = 0
        
        for note in queryset:
            if not note.follow_up_date:
                continue
            
            # Try to find user email
            user_email = None
            try:
                user = StaffUser.objects.filter(
                    username__iexact=note.staff_member
                ).first()
                if not user:
                    name_parts = note.staff_member.split()
                    if len(name_parts) >= 2:
                        user = StaffUser.objects.filter(
                            first_name__iexact=name_parts[0],
                            last_name__iexact=name_parts[-1]
                        ).first()
                if user and user.email:
                    user_email = user.email
            except:
                pass
            
            if not user_email:
                from django.conf import settings as django_settings
                user_email = getattr(django_settings, 'CASE_NOTE_ALERT_EMAIL', None)
                if not user_email:
                    admin_user = StaffUser.objects.filter(is_superuser=True).first()
                    if admin_user and admin_user.email:
                        user_email = admin_user.email
            
            if user_email:
                if send_followup_alert(note, user_email):
                    sent += 1
                else:
                    errors += 1
            else:
                errors += 1
        
        if sent > 0:
            self.message_user(request, f'✅ Sent {sent} follow-up alert email(s)')
        if errors > 0:
            self.message_user(request, f'❌ {errors} error(s) occurred', level='error')
    
    send_followup_alerts_action.short_description = "Send follow-up alert emails for selected case notes"

    def save_model(self, request, obj, form, change):
        """Stamp staff member from logged-in user when missing."""
        if not obj.staff_member:
            obj.staff_member = request.user.get_full_name() or request.user.username
        super().save_model(request, obj, form, change)
    
    def changelist_view(self, request, extra_context=None):
        """Add overdue follow-ups alert to changelist"""
        response = super().changelist_view(request, extra_context)
        
        if hasattr(response, 'context_data'):
            overdue_qs = CaseNote.objects.filter(
                follow_up_date__lt=timezone.now().date()
            ).exclude(follow_up_date__isnull=True)
            overdue_count = overdue_qs.count()
            
            if overdue_count > 0:
                from django.contrib import messages
                today = timezone.now().date()
                overdue_30 = overdue_qs.filter(follow_up_date__lte=today - timedelta(days=30)).count()
                overdue_60 = overdue_qs.filter(follow_up_date__lte=today - timedelta(days=60)).count()
                overdue_90 = overdue_qs.filter(follow_up_date__lte=today - timedelta(days=90)).count()
                messages.warning(
                    request,
                    (
                        f'⚠️ Overdue follow-ups: {overdue_count} total '
                        f'({overdue_30} at 30+ days, {overdue_60} at 60+ days, {overdue_90} at 90+ days).'
                    ),
                    extra_tags='alert'
                )
        
        return response

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'phone', 'email', 'training_interest', 'status', 'program_completed_date', 'job_placed', 'has_resume', 'case_notes_count', 'created_at']
    list_filter = ['status', 'training_interest', 'job_placed', 'neighborhood', 'sf_resident', 'employment_status', 'created_at', 'program_completed_date']
    search_fields = ['first_name', 'last_name', 'phone', 'job_title', 'job_company']
    readonly_fields = ['created_at', 'updated_at', 'case_notes_count', 'masked_ssn', 'resume_preview', 'worker_portal_summary']
    date_hierarchy = 'created_at'
    inlines = [WorkAssignmentInline, DocumentInline, CaseNoteInline]  # Schedule, documents + case notes
    list_per_page = 25
    show_full_result_count = False
    
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
        ]
        return custom_urls + urls

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
        for inst in instances:
            if isinstance(inst, Document) and not inst.uploaded_by:
                inst.uploaded_by = request.user.get_full_name() or request.user.username
            if isinstance(inst, WorkAssignment) and not inst.assigned_by:
                inst.assigned_by = request.user.get_full_name() or request.user.username or 'Admin'
            inst.save()
        formset.save_m2m()
    
    def add_case_note_view(self, request, object_id):
        """Quick add case note view"""
        from django.shortcuts import get_object_or_404, redirect
        from django.contrib import messages
        from django.template.response import TemplateResponse
        
        client = get_object_or_404(Client, pk=object_id)
        
        if request.method == 'POST':
            try:
                note = CaseNote.objects.create(
                    client=client,
                    staff_member=request.user.get_full_name() or request.user.username,
                    note_type=request.POST.get('note_type', 'general'),
                    content=request.POST.get('content', ''),
                    next_steps=request.POST.get('next_steps', '') or None,
                    follow_up_date=request.POST.get('follow_up_date') or None,
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
        ('Documents', {
            'fields': ('resume', 'resume_preview'),
            'description': 'Upload a resume or view existing resume. Preview and download links are available below.'
        }),
        ('Status & Tracking', {
            'fields': ('status', 'staff_name')
        }),
        ('Program Completion & Job Placement', {
            'fields': ('program_completed_date', 'job_placed', 'job_placement_date', 'job_title', 'job_company', 'job_hourly_wage')
        }),
        ('Worker Portal + Schedule', {
            'fields': ('worker_portal_summary',),
            'description': 'Use the Work Assignments section below to schedule PitStop shifts for this worker.',
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
    
    def resume_preview(self, obj):
        """Display preview/download link for resume, or re-upload prompt if missing."""
        if not obj.resume:
            return format_html('<span style="color: #999;">No resume uploaded</span>')
        
        filename = obj.resume.name.split('/')[-1]
        
        try:
            download_url = obj.resume_download_url
        except FileNotFoundError:
            download_url = None
        except Exception as e:
            logging.getLogger('clients').error('Resume preview error for Client %s: %s', obj.pk, e)
            download_url = None
        
        if not download_url:
            return format_html(
                '<div style="padding: 12px; background: #fff3cd; border: 1px solid #ffc107; border-radius: 6px;">'
                '<strong style="color: #856404;">⚠️ File Missing from Azure Storage</strong><br>'
                '<span style="color: #856404;">File <code>{}</code> is not in Azure.</span><br>'
                '<span style="color: #856404;">Use the "Choose File" button above to re-upload it, then click Save.</span>'
                '</div>',
                filename
            )
        
        file_type = obj.get_resume_file_type()
        preview_html = '<div style="margin-top: 10px;">'
        
        if file_type == 'pdf':
            preview_html += f'<div style="margin-bottom: 10px;"><strong>Preview:</strong><br><iframe src="{download_url}" width="100%" height="600px" style="border: 1px solid #ddd; border-radius: 4px;"></iframe></div>'
        elif file_type == 'image':
            preview_html += f'<div style="margin-bottom: 10px;"><strong>Preview:</strong><br><img src="{download_url}" alt="{filename}" style="max-width: 100%; max-height: 400px; border: 1px solid #ddd; border-radius: 4px; padding: 5px;"></div>'
        else:
            preview_html += f'<div style="margin-bottom: 10px; padding: 10px; background: #f5f5f5; border-radius: 4px;"><strong>File:</strong> {filename}<br><em>Preview not available for this file type. Please download to view.</em></div>'
        
        preview_html += f'<div><a href="{download_url}" target="_blank" style="display: inline-block; padding: 8px 16px; background: #1976d2; color: white; text-decoration: none; border-radius: 4px; margin-top: 10px;">📥 Download Resume</a></div>'
        preview_html += '</div>'
        return format_html(preview_html)
    resume_preview.short_description = 'Resume Preview & Download'
    
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
        assignments_url = (
            reverse('admin:clients_workassignment_changelist')
            + f'?client__id__exact={obj.pk}'
        )
        return format_html(
            '<div style="padding: 10px; background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; line-height: 1.5;">'
            '<strong>Portal:</strong> {}<br>'
            '<strong>Scheduled this week:</strong> {}<br>'
            '<a href="{}">Open worker account</a> · '
            '<a href="{}">View schedule</a>'
            '</div>',
            'On' if account.is_active else 'Off',
            _format_hours(hours),
            account_url,
            assignments_url,
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
    
    def get_fields(self, request, obj=None):
        """Allow superusers to edit actual SSN field"""
        self._current_request = request
        fields = list(super().get_fields(request, obj))
        
        # For superusers, show both masked view and editable SSN field
        if request.user.is_superuser and obj:
            # Find where masked_ssn is and add actual ssn field after it
            personal_info_fields = list(self.fieldsets[0][1]['fields'])
            if 'masked_ssn' in personal_info_fields and 'ssn' not in personal_info_fields:
                # Replace masked_ssn with ssn for superusers in edit mode
                idx = personal_info_fields.index('masked_ssn')
                personal_info_fields[idx] = 'ssn'
                self.fieldsets = (
                    ('Personal Information', {
                        'fields': tuple(personal_info_fields)
                    }),
                ) + self.fieldsets[1:]
        
        return fields
    
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(case_notes_total=Count('casenotes'))
    
    actions = [
        'mark_active',
        'mark_completed',
        'mark_job_placed',
        'create_worker_accounts',
        'text_missing_documents',
        'export_to_csv',
        'export_program_report',
        'export_job_placement_report',
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
    
    def mark_job_placed(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(job_placed=True, job_placement_date=timezone.now().date())
        self.message_user(request, f'{updated} clients marked as job placed with today\'s date.')
    mark_job_placed.short_description = "Mark selected clients as job placed"
    
    def export_program_report(self, request, queryset):
        """Export program completion and job placement report"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="program_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Client Name', 'Phone', 'Email', 'Program', 'Status', 'Program Completed Date',
            'Job Placed', 'Job Placement Date', 'Job Title', 'Company', 'Hourly Wage', 'Created Date'
        ])
        
        for client in queryset.select_related():
            writer.writerow([
                client.full_name,
                client.phone,
                client.email or '',
                client.get_training_interest_display(),
                client.get_status_display(),
                client.program_completed_date.strftime('%Y-%m-%d') if client.program_completed_date else '',
                'Yes' if client.job_placed else 'No',
                client.job_placement_date.strftime('%Y-%m-%d') if client.job_placement_date else '',
                client.job_title or '',
                client.job_company or '',
                f'${client.job_hourly_wage}' if client.job_hourly_wage else '',
                client.created_at.strftime('%Y-%m-%d')
            ])
        
        return response
    export_program_report.short_description = "Export program completion & job placement report"
    
    def export_job_placement_report(self, request, queryset):
        """Export detailed job placement report for placed clients only"""
        placed_clients = queryset.filter(job_placed=True)
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="job_placements_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Client Name', 'Phone', 'Email', 'Program Completed', 'Job Title', 'Company', 
            'Hourly Wage', 'Placement Date', 'Days to Placement', 'Program Type'
        ])
        
        for client in placed_clients:
            days_to_placement = ''
            if client.program_completed_date and client.job_placement_date:
                days_to_placement = (client.job_placement_date - client.program_completed_date).days
            
            writer.writerow([
                client.full_name,
                client.phone,
                client.email or '',
                client.program_completed_date.strftime('%Y-%m-%d') if client.program_completed_date else '',
                client.job_title or '',
                client.job_company or '',
                f'${client.job_hourly_wage}' if client.job_hourly_wage else '',
                client.job_placement_date.strftime('%Y-%m-%d') if client.job_placement_date else '',
                str(days_to_placement) if days_to_placement != '' else '',
                client.get_training_interest_display()
            ])
        
        return response
    export_job_placement_report.short_description = "Export job placement report (placed clients only)"
    
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


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['client', 'title', 'doc_type', 'file_size_mb', 'uploaded_by', 'created_at', 'download_link']
    list_filter = ['doc_type', 'created_at', 'uploaded_by']
    search_fields = ['client__first_name', 'client__last_name', 'title', 'uploaded_by']
    readonly_fields = ['created_at', 'updated_at', 'file_size', 'content_type', 'file_preview', 'blob_path_info']
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
        """Display preview/download link, or re-upload prompt if missing."""
        if not obj.file:
            return format_html('<span style="color: #999;">No file uploaded</span>')
        
        filename = obj.file.name.split('/')[-1]
        download_url = obj.download_url
        
        if not download_url:
            return format_html(
                '<div style="padding: 12px; background: #fff3cd; border: 1px solid #ffc107; border-radius: 6px;">'
                '<strong style="color: #856404;">⚠️ File Missing from Azure Storage</strong><br>'
                '<span style="color: #856404;">File <code>{}</code> is not in Azure.</span><br>'
                '<span style="color: #856404;">Use the "Choose File" button above to re-upload it, then click Save.</span>'
                '</div>',
                filename
            )
        
        file_type = obj.get_file_type()
        preview_html = '<div style="margin-top: 10px;">'
        
        if file_type == 'pdf':
            preview_html += f'<div style="margin-bottom: 10px;"><strong>Preview:</strong><br><iframe src="{download_url}" width="100%" height="600px" style="border: 1px solid #ddd; border-radius: 4px;"></iframe></div>'
        elif file_type == 'image':
            preview_html += f'<div style="margin-bottom: 10px;"><strong>Preview:</strong><br><img src="{download_url}" alt="{filename}" style="max-width: 100%; max-height: 400px; border: 1px solid #ddd; border-radius: 4px; padding: 5px;"></div>'
        else:
            preview_html += f'<div style="margin-bottom: 10px; padding: 10px; background: #f5f5f5; border-radius: 4px;"><strong>File:</strong> {filename}<br><em>Preview not available for this file type. Please download to view.</em></div>'
        
        preview_html += f'<div><a href="{download_url}" target="_blank" style="display: inline-block; padding: 8px 16px; background: #1976d2; color: white; text-decoration: none; border-radius: 4px; margin-top: 10px;">📥 Download Document</a></div>'
        preview_html += '</div>'
        return format_html(preview_html)
    file_preview.short_description = 'Preview & Download'
    
    def download_link(self, obj):
        """Quick download link for list view"""
        if not obj.file:
            return '-'
        download_url = obj.download_url
        if download_url:
            return format_html('<a href="{}" target="_blank">📥</a>', download_url)
        return format_html('<span style="color: #f44336;" title="File missing from Azure">⚠️</span>')
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
    list_display = ['client', 'position_applied_for', 'employment_desired', 'can_work_us', 'is_veteran', 'available_days_summary', 'created_at']
    list_filter = ['employment_desired', 'can_work_us', 'is_veteran', 'created_at']
    search_fields = ['client__first_name', 'client__last_name', 'position_applied_for']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'updated_at', 'schedule_summary']
    
    def available_days_summary(self, obj):
        """Show summary of available days"""
        if not obj.weekly_schedule:
            return "No schedule set"
        days_with_times = [day for day, times in obj.weekly_schedule.items() if times]
        return ", ".join(days_with_times) if days_with_times else "No days available"
    available_days_summary.short_description = 'Available Days'
    
    def schedule_summary(self, obj):
        """Show detailed schedule summary"""
        if not obj.weekly_schedule:
            return "No schedule set"
        
        summary = []
        for day, times in obj.weekly_schedule.items():
            if times:
                time_labels = []
                for time_code in times:
                    # Convert time code to label
                    for choice in obj.SHIFT_CHOICES:
                        if choice[0] == time_code:
                            time_labels.append(choice[1])
                            break
                summary.append(f"{day}: {', '.join(time_labels)}")
        
        return format_html('<br>'.join(summary)) if summary else "No availability set"
    schedule_summary.short_description = 'Weekly Schedule'


@admin.register(JobPlacement)
class JobPlacementAdmin(admin.ModelAdmin):
    list_display = [
        'client',
        'employer',
        'job_title',
        'work_type',
        'hourly_rate',
        'start_date',
        'created_by_name',
        'created_at',
    ]
    list_filter = ['work_type', 'start_date', 'created_at', 'created_by_name']
    search_fields = [
        'client__first_name',
        'client__last_name',
        'employer',
        'job_title',
        'created_by_name',
    ]
    autocomplete_fields = ['client', 'created_by_user']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Placement', {
            'fields': (
                'client',
                'employer',
                'job_title',
                'work_type',
                'hourly_rate',
                'start_date',
                'employer_address',
                'notes',
            )
        }),
        ('Audit', {
            'fields': ('created_by_user', 'created_by_name', 'created_at', 'updated_at')
        }),
    )


# ========================================
# Worker Portal Admin Interfaces
# ========================================

class WorkerShiftProofInline(admin.TabularInline):
    """Recent worker photo/location submissions shown on the roster profile."""

    model = WorkerShiftProof
    extra = 0
    can_delete = False
    fields = [
        'assignment',
        'submitted_at',
        'photo_preview',
        'geo_status',
        'geo_basic_ok',
        'geo_basic_note',
    ]
    readonly_fields = fields
    ordering = ['-submitted_at']
    max_num = 0
    verbose_name = 'Photo/location check-in'
    verbose_name_plural = 'Photo/location check-ins (latest first)'

    def has_add_permission(self, request, obj=None):
        return False

    def photo_preview(self, obj):
        if not obj or not obj.photo:
            return '—'
        return format_html(
            '<a href="{}" target="_blank"><img src="{}" style="max-height: 80px; border-radius: 6px;" /></a>',
            obj.photo.url,
            obj.photo.url,
        )

    photo_preview.short_description = 'Photo'


class AssignmentShiftProofInline(admin.TabularInline):
    """Photo/location submissions shown directly on an assignment."""

    model = WorkerShiftProof
    extra = 0
    can_delete = False
    fields = [
        'worker_account',
        'submitted_at',
        'photo_preview',
        'geo_status',
        'geo_basic_ok',
        'geo_basic_note',
    ]
    readonly_fields = fields
    ordering = ['-submitted_at']
    max_num = 0
    verbose_name = 'Photo/location check-in'
    verbose_name_plural = 'Photo/location check-ins'

    def has_add_permission(self, request, obj=None):
        return False

    def photo_preview(self, obj):
        if not obj or not obj.photo:
            return '—'
        return format_html(
            '<a href="{}" target="_blank"><img src="{}" style="max-height: 80px; border-radius: 6px;" /></a>',
            obj.photo.url,
            obj.photo.url,
        )

    photo_preview.short_description = 'Photo'


@admin.register(WorkerAccount)
class WorkerAccountAdmin(admin.ModelAdmin):
    """Primary PitStop roster focused on clock in/out tracking."""
    list_display = [
        'client',
        'phone',
        'worker_status',
        'portal_access_display',
        'availability_display',
        'weekly_hours_check',
        'last_punch_display',
    ]
    list_filter = ['worker_status', 'is_active', 'is_available', 'created_at']
    search_fields = ['client__first_name', 'client__last_name', 'phone']
    readonly_fields = [
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
        ('Worker Information', {
            'fields': ('client', 'phone', 'worker_status', 'is_available'),
            'description': 'Phone is saved as digits only so workers can log in with their mobile keypad.',
        }),
        ('Portal access', {
            'fields': ('is_active', 'last_login', 'login_attempts', 'locked_until'),
            'description': 'Uncheck “Portal access” to block login. PIN reset: use action “Reset PIN to last 4 digits of phone”.',
        }),
        ('Hours + clock logs', {
            'fields': ('weekly_hours_check', 'total_hours_display', 'last_punch_display', 'related_records_links'),
            'description': 'Clock-in/out hours are geolocation validated against PitStop work sites.',
        }),
        ('Account Management', {
            'fields': ('created_by', 'created_at', 'notes', 'follow_up_notes')
        }),
        ('Security', {
            'fields': ('pin_hash',),
            'classes': ('collapse',),
            'description': 'PIN is hashed. Use list action to reset to last 4 digits of the stored phone number.'
        }),
    )
    
    actions = [
        'mark_applicant',
        'mark_active_worker',
        'mark_inactive_worker',
        'set_available',
        'set_unavailable',
        'approve_accounts',
        'deactivate_accounts',
        'reset_pins',
        'unlock_accounts',
    ]

    def portal_access_display(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green; font-weight: bold;">✓ On</span>')
        return format_html('<span style="color: #999;">Off</span>')
    portal_access_display.short_description = 'Portal'

    def availability_display(self, obj):
        if obj.is_available:
            return format_html('<span style="color: green; font-weight: bold;">Available</span>')
        return format_html('<span style="color: #999;">Not available</span>')
    availability_display.short_description = 'Availability'

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
            punch.clock_in_at.strftime('%b %d, %Y %I:%M %p'),
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
    
    def is_locked(self, obj):
        """Show if account is currently locked"""
        if obj.is_locked:
            return format_html('<span style="color: red;">🔒 Locked</span>')
        return format_html('<span style="color: green;">✓ Active</span>')
    is_locked.short_description = 'Lock Status'

    def mark_applicant(self, request, queryset):
        updated = queryset.update(worker_status=WorkerAccount.STATUS_APPLICANT)
        self.message_user(request, f'{updated} roster row(s) marked applicant.')
    mark_applicant.short_description = 'Set status: Applicant'

    def mark_active_worker(self, request, queryset):
        updated = queryset.update(worker_status=WorkerAccount.STATUS_ACTIVE)
        self.message_user(request, f'{updated} roster row(s) marked active worker.')
    mark_active_worker.short_description = 'Set status: Active Worker'

    def mark_inactive_worker(self, request, queryset):
        updated = queryset.update(worker_status=WorkerAccount.STATUS_INACTIVE, is_available=False)
        self.message_user(request, f'{updated} roster row(s) marked inactive.')
    mark_inactive_worker.short_description = 'Set status: Inactive'

    def set_available(self, request, queryset):
        updated = queryset.update(is_available=True)
        self.message_user(request, f'{updated} worker(s) marked available.')
    set_available.short_description = 'Set availability: Available'

    def set_unavailable(self, request, queryset):
        updated = queryset.update(is_available=False)
        self.message_user(request, f'{updated} worker(s) marked not available.')
    set_unavailable.short_description = 'Set availability: Not available'
    
    def approve_accounts(self, request, queryset):
        """Turn portal on and send welcome emails (same as checking Portal access for each row)."""
        from .notifications import send_worker_welcome_email

        approved = 0
        emailed = 0
        for account in queryset.filter(is_active=False):
            account.is_active = True
            account.save()
            approved += 1
            if send_worker_welcome_email(account):
                emailed += 1

        msg = f'{approved} account(s) enabled for portal.'
        if emailed:
            msg += f' {emailed} welcome email(s) sent.'
        if approved > emailed and approved:
            msg += f' {approved - emailed} skipped (no email on file).'
        if approved == 0:
            msg = 'No changes — selected accounts already had portal access on.'
        self.message_user(request, msg)
    approve_accounts.short_description = 'Enable portal + send welcome email (if inactive)'
    
    def deactivate_accounts(self, request, queryset):
        """Bulk disable worker portal logins."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'Portal login disabled for {updated} account(s).')
    deactivate_accounts.short_description = 'Disable portal login'
    
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


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    """Admin interface for worker-submitted service requests"""
    list_display = ['title', 'work_site', 'submitted_by', 'issue_type', 'priority', 'status', 'created_at', 'is_overdue']
    list_filter = ['status', 'priority', 'issue_type', 'work_site', 'created_at']
    search_fields = ['title', 'description', 'submitted_by__first_name', 'submitted_by__last_name']
    readonly_fields = ['submitted_by', 'created_at', 'updated_at', 'response_time_display', 'resolution_time_display', 'photo_preview']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Request Information', {
            'fields': ('submitted_by', 'work_site', 'issue_type', 'title', 'description', 'location_detail')
        }),
        ('Priority & Status', {
            'fields': ('priority', 'status')
        }),
        ('Evidence', {
            'fields': ('photo', 'photo_preview')
        }),
        ('Response & Resolution', {
            'fields': ('acknowledged_by', 'acknowledged_at', 'assigned_to', 'resolved_at', 'resolution_notes')
        }),
        ('Metrics', {
            'fields': ('response_time_display', 'resolution_time_display'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['acknowledge_requests', 'mark_in_progress', 'mark_resolved']
    
    def is_overdue(self, obj):
        """Show overdue status with color"""
        if obj.is_overdue:
            return format_html('<span style="color: red; font-weight: bold;">⚠️ OVERDUE</span>')
        return format_html('<span style="color: green;">✓ On Track</span>')
    is_overdue.short_description = 'Status'
    
    def photo_preview(self, obj):
        """Show photo preview"""
        if obj.photo:
            return format_html('<img src="{}" style="max-width: 300px; max-height: 300px;" />', obj.photo.url)
        return "No photo"
    photo_preview.short_description = 'Photo Preview'
    
    def response_time_display(self, obj):
        """Show response time in human-readable format"""
        rt = obj.response_time
        if rt:
            hours = rt.total_seconds() / 3600
            if hours < 1:
                return f"{int(rt.total_seconds() / 60)} minutes"
            return f"{hours:.1f} hours"
        return "Not acknowledged yet"
    response_time_display.short_description = 'Response Time'
    
    def resolution_time_display(self, obj):
        """Show resolution time in human-readable format"""
        rt = obj.resolution_time
        if rt:
            hours = rt.total_seconds() / 3600
            if hours < 24:
                return f"{hours:.1f} hours"
            return f"{hours / 24:.1f} days"
        return "Not resolved yet"
    resolution_time_display.short_description = 'Resolution Time'
    
    def acknowledge_requests(self, request, queryset):
        """Acknowledge selected requests"""
        from django.utils import timezone
        updated = queryset.filter(status='open').update(
            status='acknowledged',
            acknowledged_by=request.user.get_full_name() or request.user.username,
            acknowledged_at=timezone.now()
        )
        self.message_user(request, f'{updated} request(s) acknowledged.')
    acknowledge_requests.short_description = 'Acknowledge selected requests'
    
    def mark_in_progress(self, request, queryset):
        """Mark requests as in progress"""
        updated = queryset.exclude(status__in=['resolved', 'closed']).update(status='in_progress')
        self.message_user(request, f'{updated} request(s) marked in progress.')
    mark_in_progress.short_description = 'Mark as In Progress'
    
    def mark_resolved(self, request, queryset):
        """Mark requests as resolved"""
        from django.utils import timezone
        updated = 0
        for req in queryset.exclude(status__in=['resolved', 'closed']):
            req.status = 'resolved'
            req.resolved_at = timezone.now()
            req.save()
            updated += 1
        self.message_user(request, f'{updated} request(s) marked resolved.')
    mark_resolved.short_description = 'Mark as Resolved'


@admin.register(WorkSite)
class WorkSiteAdmin(admin.ModelAdmin):
    """Must register before OpenShiftAdmin so autocomplete_fields → work_site passes admin.E040."""

    list_display = ['name', 'neighborhood', 'site_type', 'latitude', 'longitude', 'is_active']
    list_filter = ['is_active', 'site_type', 'neighborhood']
    search_fields = ['name', 'address', 'neighborhood', 'supervisor_name', 'supervisor_email']


class ShiftCoverInterestInline(admin.TabularInline):
    model = ShiftCoverInterest
    extra = 0
    readonly_fields = ['created_at']
    autocomplete_fields = ['worker_account']
    fields = ['worker_account', 'status', 'staff_note', 'created_at']


@admin.register(OpenShift)
class OpenShiftAdmin(admin.ModelAdmin):
    """Post shifts that need coverage; active workers get email or SMS outreach."""

    list_display = [
        'role_title',
        'shift_date',
        'time_range',
        'work_site',
        'is_open',
        'interest_count',
        'created_at',
    ]
    list_filter = ['is_open', 'shift_date', 'work_site']
    search_fields = ['role_title', 'notes', 'location_label', 'created_by']
    date_hierarchy = 'shift_date'
    inlines = [ShiftCoverInterestInline]
    # No autocomplete_fields for work_site — avoids admin.E040 if WorkSite admin
    # ordering/registry differs on some hosts; use the select dropdown instead.
    fieldsets = (
        (
            'Shift',
            {
                'fields': (
                    'role_title',
                    'work_site',
                    'location_label',
                    'shift_date',
                    'start_time',
                    'end_time',
                    'notes',
                )
            },
        ),
        (
            'Staff',
            {
                'fields': ('is_open', 'created_by'),
                'description': 'Saving an open shift notifies current active PitStop workers. Uncheck “Is open” when the shift is filled.',
            },
        ),
    )

    def time_range(self, obj):
        if obj.start_time and obj.end_time:
            return f'{obj.start_time.strftime("%I:%M %p")} – {obj.end_time.strftime("%I:%M %p")}'
        return '—'

    time_range.short_description = 'Time'

    def interest_count(self, obj):
        return obj.cover_interests.count()

    interest_count.short_description = 'Interests'

    def save_model(self, request, obj, form, change):
        if not (obj.created_by or '').strip():
            obj.created_by = request.user.get_full_name() or request.user.username
        super().save_model(request, obj, form, change)


@admin.register(ShiftCoverInterest)
class ShiftCoverInterestAdmin(admin.ModelAdmin):
    list_display = ['open_shift', 'worker_name', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = [
        'worker_account__client__first_name',
        'worker_account__client__last_name',
        'open_shift__role_title',
    ]
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['worker_account', 'open_shift']

    def worker_name(self, obj):
        return obj.worker_account.client.full_name

    worker_name.short_description = 'Worker'


@admin.register(WorkerShiftProof)
class WorkerShiftProofAdmin(admin.ModelAdmin):
    """Staff review of worker photo/location check-ins."""

    list_display = [
        'worker_name',
        'assignment',
        'submitted_at',
        'geo_status',
        'geo_basic_ok',
        'photo_link',
    ]
    list_filter = ['assignment__assignment_date', 'geo_status', 'geo_basic_ok', 'submitted_at']
    search_fields = [
        'worker_account__client__first_name',
        'worker_account__client__last_name',
        'worker_account__phone',
        'assignment__work_site__name',
        'staff_note',
    ]
    readonly_fields = [
        'worker_account',
        'assignment',
        'photo_preview',
        'submitted_at',
        'client_reported_at',
        'latitude',
        'longitude',
        'accuracy_meters',
        'geo_status',
        'geo_error',
        'geo_basic_ok',
        'geo_basic_note',
    ]
    fields = [
        'worker_account',
        'assignment',
        'photo_preview',
        'submitted_at',
        'client_reported_at',
        'latitude',
        'longitude',
        'accuracy_meters',
        'geo_status',
        'geo_basic_ok',
        'geo_basic_note',
        'geo_error',
        'staff_note',
    ]
    autocomplete_fields = ['worker_account', 'assignment']
    date_hierarchy = 'submitted_at'

    def has_add_permission(self, request):
        return False

    def worker_name(self, obj):
        return obj.worker_account.client.full_name

    worker_name.short_description = 'Worker'

    def photo_link(self, obj):
        if not obj.photo:
            return '—'
        return format_html('<a href="{}" target="_blank">Open photo</a>', obj.photo.url)

    photo_link.short_description = 'Photo'

    def photo_preview(self, obj):
        if not obj.photo:
            return '—'
        return format_html(
            '<a href="{}" target="_blank"><img src="{}" style="max-width: 420px; border-radius: 8px;" /></a>',
            obj.photo.url,
            obj.photo.url,
        )

    photo_preview.short_description = 'Photo'


@admin.register(WorkerPortalNote)
class WorkerPortalNoteAdmin(admin.ModelAdmin):
    list_display = ['worker_name', 'note_type', 'is_read_by_staff', 'created_at']
    list_filter = ['note_type', 'is_read_by_staff', 'created_at']
    search_fields = [
        'worker_account__client__first_name',
        'worker_account__client__last_name',
        'worker_account__phone',
        'content',
        'staff_response',
    ]
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['worker_account']

    def worker_name(self, obj):
        return obj.worker_account.client.full_name

    worker_name.short_description = 'Worker'


@admin.register(WorkerTimeOffRequest)
class WorkerTimeOffRequestAdmin(admin.ModelAdmin):
    list_display = ['worker_name', 'start_date', 'end_date', 'status', 'created_at']
    list_filter = ['status', 'start_date', 'end_date', 'created_at']
    search_fields = [
        'worker_account__client__first_name',
        'worker_account__client__last_name',
        'worker_account__phone',
        'reason',
        'staff_note',
    ]
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['worker_account']

    def worker_name(self, obj):
        return obj.worker_account.client.full_name

    worker_name.short_description = 'Worker'


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
    """Clock in/out log with geofence validation details."""

    list_display = [
        'worker_account',
        'work_site',
        'clock_in_at',
        'clock_out_at',
        'clock_in_geo_basic_ok',
        'clock_out_geo_basic_ok',
    ]
    list_filter = ['work_site', 'clock_in_geo_status', 'clock_out_geo_status', 'clock_in_at']
    search_fields = [
        'worker_account__client__first_name',
        'worker_account__client__last_name',
        'worker_account__phone',
        'work_site__name',
    ]
    readonly_fields = [field.name for field in WorkerTimePunch._meta.fields]
    date_hierarchy = 'clock_in_at'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(WorkAssignment)
class WorkAssignmentAdmin(admin.ModelAdmin):
    """Staff scheduling view for PitStop worker assignments."""

    list_display = [
        'client',
        'worker_phone',
        'work_site',
        'assignment_date',
        'time_range',
        'status',
        'confirmed_by_client',
        'scheduled_hours',
        'photo_checkins',
        'assigned_by',
    ]
    list_filter = ['status', 'assignment_date', 'work_site', 'confirmed_by_client']
    search_fields = [
        'client__first_name',
        'client__last_name',
        'work_site__name',
        'assigned_by',
    ]
    date_hierarchy = 'assignment_date'
    readonly_fields = ['created_at', 'updated_at', 'photo_checkins', 'scheduled_hours']
    inlines = [AssignmentShiftProofInline]
    actions = ['mark_confirmed', 'mark_in_progress', 'mark_completed']

    fieldsets = (
        ('Worker + Site', {
            'fields': ('client', 'work_site'),
        }),
        ('Schedule', {
            'fields': ('assignment_date', 'start_time', 'end_time', 'scheduled_hours', 'status', 'confirmed_by_client', 'confirmed_at'),
        }),
        ('Worker check-in', {
            'fields': ('photo_checkins',),
            'description': 'Workers submit photo/location proof only when a supervisor asks.',
        }),
        ('Staff Notes', {
            'fields': ('assigned_by', 'assignment_notes', 'performance_notes'),
        }),
        ('Call-out', {
            'fields': ('called_out_at', 'callout_reason', 'replacement_found', 'replacement_client'),
            'classes': ('collapse',),
        }),
        ('Completion', {
            'fields': ('hours_worked',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def save_model(self, request, obj, form, change):
        if not (obj.assigned_by or '').strip():
            obj.assigned_by = request.user.get_full_name() or request.user.username or 'Admin'
        super().save_model(request, obj, form, change)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'assigned_by' in form.base_fields:
            form.base_fields['assigned_by'].required = False
        return form

    def time_range(self, obj):
        if obj.start_time and obj.end_time:
            return f'{obj.start_time.strftime("%I:%M %p")} - {obj.end_time.strftime("%I:%M %p")}'
        return '—'

    time_range.short_description = 'Time'

    def worker_phone(self, obj):
        account = getattr(obj.client, 'worker_account', None)
        return account.phone if account else obj.client.phone

    worker_phone.short_description = 'Phone'

    def scheduled_hours(self, obj):
        if not obj or not obj.assignment_date or not obj.start_time or not obj.end_time:
            return '—'
        return _format_hours(_assignment_duration_hours(obj))

    scheduled_hours.short_description = 'Scheduled hours'

    def photo_checkins(self, obj):
        if not obj or not obj.pk:
            return 'Save first to view photo check-ins.'
        count = obj.shift_proofs.count()
        url = reverse('admin:clients_workershiftproof_changelist') + f'?assignment__id__exact={obj.pk}'
        if not count:
            return format_html('<a href="{}">No photo check-ins yet</a>', url)
        return format_html('<a href="{}">{} photo/location check-in(s)</a>', url, count)

    photo_checkins.short_description = 'Photo check-ins'

    def mark_confirmed(self, request, queryset):
        updated = queryset.update(status='confirmed', confirmed_by_client=True, confirmed_at=timezone.now())
        self.message_user(request, f'{updated} assignment(s) marked confirmed.')

    mark_confirmed.short_description = 'Mark selected assignments confirmed'

    def mark_in_progress(self, request, queryset):
        updated = queryset.update(status='in_progress')
        self.message_user(request, f'{updated} assignment(s) marked in progress.')

    mark_in_progress.short_description = 'Mark selected assignments in progress'

    def mark_completed(self, request, queryset):
        updated = queryset.update(status='completed')
        self.message_user(request, f'{updated} assignment(s) marked completed.')

    mark_completed.short_description = 'Mark selected assignments completed'


# Iceboxed modules — hidden from admin to keep iPad clock workflow lean.
for _model in (
    OpenShift,
    ServiceRequest,
    ShiftCoverInterest,
    WorkAssignment,
    WorkerPortalNote,
    WorkerShiftProof,
    WorkerTimeOffRequest,
):
    try:
        admin.site.unregister(_model)
    except admin.sites.NotRegistered:
        pass

