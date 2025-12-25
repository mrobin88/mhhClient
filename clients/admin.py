from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.db.models import Count, Q
from datetime import datetime, timedelta
import csv
import io
from django.shortcuts import redirect
from django.contrib import messages
from django.utils import timezone
from .models import Client, CaseNote, Document, PitStopApplication

# PDF generation removed - WeasyPrint no longer used
WEASYPRINT_AVAILABLE = False


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
            'all': ()  # 'admin/css/custom-case-notes.css' commented out
        }
        js = ('admin/js/case-notes-helper.js',)
    
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
    
    def changelist_view(self, request, extra_context=None):
        """Add overdue follow-ups alert to changelist"""
        response = super().changelist_view(request, extra_context)
        
        if hasattr(response, 'context_data'):
            overdue_count = CaseNote.objects.filter(
                follow_up_date__lt=timezone.now().date()
            ).exclude(follow_up_date__isnull=True).count()
            
            if overdue_count > 0:
                from django.contrib import messages
                messages.warning(
                    request,
                    f'⚠️ You have {overdue_count} case note(s) with overdue follow-ups! Check the list below.',
                    extra_tags='alert'
                )
        
        return response

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'phone', 'email', 'training_interest', 'status', 'job_placed', 'program_completed_date', 'has_resume', 'case_notes_count', 'created_at']
    list_filter = ['status', 'training_interest', 'job_placed', 'neighborhood', 'sf_resident', 'employment_status', 'created_at', 'program_completed_date']
    search_fields = ['first_name', 'last_name', 'phone', 'job_title', 'job_company']
    readonly_fields = ['created_at', 'updated_at', 'case_notes_count', 'masked_ssn']
    date_hierarchy = 'created_at'
    inlines = [CaseNoteInline]  # Add case notes as inline list
    
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
            'fields': ('resume',)
        }),
        ('Status & Tracking', {
            'fields': ('status', 'staff_name')
        }),
        ('Program Completion & Job Placement', {
            'fields': ('program_completed_date', 'job_placed', 'job_placement_date', 'job_title', 'job_company', 'job_hourly_wage')
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
    
    def case_notes_count(self, obj):
        count = obj.casenotes.count()
        if count > 0:
            url = reverse('admin:clients_casenote_changelist') + f'?client__id__exact={obj.id}'
            return format_html('<a href="{}">{} notes</a>', url, count)
        return '0 notes'
    case_notes_count.short_description = 'Case Notes'
    
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
        return super().get_queryset(request).prefetch_related('casenotes')
    
    actions = ['mark_active', 'mark_completed', 'mark_job_placed', 'export_to_csv', 'export_program_report', 'export_job_placement_report', 'export_client_profiles_pdf']
    
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
    list_display = ['client', 'title', 'doc_type', 'file_size_mb', 'uploaded_by', 'created_at']
    list_filter = ['doc_type', 'created_at', 'uploaded_by']
    search_fields = ['client__first_name', 'client__last_name', 'title', 'uploaded_by']
    readonly_fields = ['created_at', 'updated_at', 'file_size', 'content_type']
    date_hierarchy = 'created_at'
    actions = ['safe_delete_selected']
    
    fieldsets = (
        ('Document Information', {
            'fields': ('client', 'title', 'doc_type', 'file')
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
