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
import logging
import os
from django.shortcuts import redirect
from django.contrib import messages
from django.utils import timezone
from .models import Client, CaseNote, Document, PitStopApplication
from .models_extensions import WorkSite, ClientAvailability, WorkAssignment, CallOutLog, WorkerAccount, ServiceRequest

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
    list_display = ['full_name', 'phone', 'email', 'training_interest', 'status', 'program_completed_date', 'job_placed', 'has_resume', 'case_notes_count', 'created_at']
    list_filter = ['status', 'training_interest', 'job_placed', 'neighborhood', 'sf_resident', 'employment_status', 'created_at', 'program_completed_date']
    search_fields = ['first_name', 'last_name', 'phone', 'job_title', 'job_company']
    readonly_fields = ['created_at', 'updated_at', 'case_notes_count', 'masked_ssn', 'resume_preview']
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
            'fields': ('resume', 'resume_preview'),
            'description': 'Upload a resume or view existing resume. Preview and download links are available below.'
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
    
    def program_duration(self, obj):
        """Display program duration in list view"""
        if not obj.program_start_date:
            return format_html('<span style="color: #999;">-</span>')
        
        duration = obj.program_duration_display
        # Highlight if 1+ year in program
        if obj.is_in_program_one_year:
            return format_html(
                '<span style="background: #fff3cd; padding: 4px 8px; border-radius: 4px; font-weight: bold;">🎉 {}</span>',
                duration
            )
        return format_html('<span style="color: #2e7d32;">{}</span>', duration)
    program_duration.short_description = 'Program Duration'
    program_duration.admin_order_field = 'program_start_date'
    
    def program_duration_info(self, obj):
        """Display detailed program duration info in edit view"""
        if not obj.program_start_date:
            return format_html('<span style="color: #999;">No program start date set</span>')
        
        from datetime import date
        info_html = f'<div style="padding: 10px; background: #f5f5f5; border-radius: 4px;">'
        info_html += f'<strong>Started:</strong> {obj.program_start_date.strftime("%B %d, %Y")}<br>'
        info_html += f'<strong>Duration:</strong> {obj.program_duration_display}'
        
        if obj.days_in_program:
            info_html += f' ({obj.days_in_program} days)'
        
        if obj.is_in_program_one_year:
            info_html += '<br><span style="color: #2e7d32; font-weight: bold;">✓ In program for 1+ year</span>'
        
        if obj.program_completed_date:
            info_html += f'<br><strong>Completed:</strong> {obj.program_completed_date.strftime("%B %d, %Y")}'
        else:
            info_html += '<br><em>Currently active in program</em>'
        
        info_html += '</div>'
        return format_html(info_html)
    program_duration_info.short_description = 'Program Duration'
    
    def resume_preview(self, obj):
        """Display preview and download link for resume"""
        if not obj.resume:
            return format_html('<span style="color: #999;">No resume uploaded</span>')
        
        try:
            download_url = obj.resume_download_url
            if not download_url:
                return format_html('<span style="color: #d32f2f;">Error: Could not generate download URL</span>')
            
            file_type = obj.get_resume_file_type()
            filename = obj.resume.name.split('/')[-1]
            
            preview_html = '<div style="margin-top: 10px;">'
            
            # Preview based on file type
            if file_type == 'pdf':
                preview_html += f'''
                <div style="margin-bottom: 10px;">
                    <strong>Preview:</strong><br>
                    <iframe src="{download_url}" width="100%" height="600px" style="border: 1px solid #ddd; border-radius: 4px;"></iframe>
                </div>
                '''
            elif file_type == 'image':
                preview_html += f'''
                <div style="margin-bottom: 10px;">
                    <strong>Preview:</strong><br>
                    <img src="{download_url}" alt="{filename}" style="max-width: 100%; max-height: 400px; border: 1px solid #ddd; border-radius: 4px; padding: 5px;">
                </div>
                '''
            else:
                preview_html += f'''
                <div style="margin-bottom: 10px; padding: 10px; background: #f5f5f5; border-radius: 4px;">
                    <strong>File:</strong> {filename}<br>
                    <em>Preview not available for this file type. Please download to view.</em>
                </div>
                '''
            
            # Download link
            preview_html += f'''
            <div>
                <a href="{download_url}" target="_blank" style="display: inline-block; padding: 8px 16px; background: #1976d2; color: white; text-decoration: none; border-radius: 4px; margin-top: 10px;">
                    📥 Download Resume
                </a>
            </div>
            '''
            
            preview_html += '</div>'
            return format_html(preview_html)
        except Exception as e:
            logging.getLogger('clients').error('Failed to generate resume preview for Client %s: %s', obj.pk, e)
            return format_html('<span style="color: #d32f2f;">Error generating preview: {}</span>', str(e))
    resume_preview.short_description = 'Resume Preview & Download'
    
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
    
    actions = ['mark_active', 'mark_completed', 'mark_job_placed', 'create_worker_accounts', 'export_to_csv', 'export_program_report', 'export_job_placement_report', 'export_client_profiles_pdf']
    
    def create_worker_accounts(self, request, queryset):
        """Create worker portal accounts for selected PitStop clients"""
        from django.contrib.auth.hashers import make_password
        
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
            
            try:
                # Generate PIN from last 4 digits of phone
                pin = client.phone[-4:] if len(client.phone) >= 4 else '1234'
                
                # Create worker account
                WorkerAccount.objects.create(
                    client=client,
                    phone=client.phone,
                    pin_hash=make_password(pin),
                    is_active=True,
                    is_approved=True,
                    created_by=request.user.username
                )
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
        """Display preview and download link for document file"""
        if not obj.file:
            return format_html('<span style="color: #999;">No file uploaded</span>')
        
        try:
            download_url = obj.download_url
            if not download_url:
                return format_html('<span style="color: #d32f2f;">Error: Could not generate download URL</span>')
            
            file_type = obj.get_file_type()
            filename = obj.file.name.split('/')[-1]
            
            preview_html = '<div style="margin-top: 10px;">'
            
            # Preview based on file type
            if file_type == 'pdf':
                preview_html += f'''
                <div style="margin-bottom: 10px;">
                    <strong>Preview:</strong><br>
                    <iframe src="{download_url}" width="100%" height="600px" style="border: 1px solid #ddd; border-radius: 4px;"></iframe>
                </div>
                '''
            elif file_type == 'image':
                preview_html += f'''
                <div style="margin-bottom: 10px;">
                    <strong>Preview:</strong><br>
                    <img src="{download_url}" alt="{filename}" style="max-width: 100%; max-height: 400px; border: 1px solid #ddd; border-radius: 4px; padding: 5px;">
                </div>
                '''
            else:
                preview_html += f'''
                <div style="margin-bottom: 10px; padding: 10px; background: #f5f5f5; border-radius: 4px;">
                    <strong>File:</strong> {filename}<br>
                    <em>Preview not available for this file type. Please download to view.</em>
                </div>
                '''
            
            # Download link
            preview_html += f'''
            <div>
                <a href="{download_url}" target="_blank" style="display: inline-block; padding: 8px 16px; background: #1976d2; color: white; text-decoration: none; border-radius: 4px; margin-top: 10px;">
                    📥 Download Document
                </a>
            </div>
            '''
            
            preview_html += '</div>'
            return format_html(preview_html)
        except Exception as e:
            logging.getLogger('clients').error('Failed to generate file preview for Document %s: %s', obj.pk, e)
            return format_html('<span style="color: #d32f2f;">Error generating preview: {}</span>', str(e))
    file_preview.short_description = 'Preview & Download'
    
    def download_link(self, obj):
        """Quick download link for list view"""
        if not obj.file:
            return '-'
        try:
            download_url = obj.download_url
            if download_url:
                return format_html('<a href="{}" target="_blank">📥</a>', download_url)
        except:
            pass
        return format_html('<a href="/api/documents/{}/download/" target="_blank">📥</a>', obj.pk)
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
                        blobs = list(container_client.list_blobs(max_results=10))
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


# ========================================
# Worker Portal Admin Interfaces
# ========================================

@admin.register(WorkerAccount)
class WorkerAccountAdmin(admin.ModelAdmin):
    """Admin interface for worker portal accounts"""
    list_display = ['client', 'phone', 'is_active', 'is_approved', 'last_login', 'login_attempts', 'is_locked']
    list_filter = ['is_active', 'is_approved', 'created_at']
    search_fields = ['client__first_name', 'client__last_name', 'phone']
    readonly_fields = ['pin_hash', 'last_login', 'login_attempts', 'locked_until', 'created_at']
    
    fieldsets = (
        ('Worker Information', {
            'fields': ('client', 'phone')
        }),
        ('Account Status', {
            'fields': ('is_active', 'is_approved', 'last_login', 'login_attempts', 'locked_until')
        }),
        ('Account Management', {
            'fields': ('created_by', 'created_at', 'notes')
        }),
        ('Security', {
            'fields': ('pin_hash',),
            'classes': ('collapse',),
            'description': 'PIN is hashed for security. To reset PIN, use the action below.'
        }),
    )
    
    actions = ['approve_accounts', 'deactivate_accounts', 'reset_pins', 'unlock_accounts']
    
    def is_locked(self, obj):
        """Show if account is currently locked"""
        if obj.is_locked:
            return format_html('<span style="color: red;">🔒 Locked</span>')
        return format_html('<span style="color: green;">✓ Active</span>')
    is_locked.short_description = 'Lock Status'
    
    def approve_accounts(self, request, queryset):
        """Bulk approve worker accounts"""
        updated = queryset.update(is_approved=True, is_active=True)
        self.message_user(request, f'{updated} account(s) approved.')
    approve_accounts.short_description = 'Approve selected accounts'
    
    def deactivate_accounts(self, request, queryset):
        """Bulk deactivate worker accounts"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} account(s) deactivated.')
    deactivate_accounts.short_description = 'Deactivate selected accounts'
    
    def reset_pins(self, request, queryset):
        """Reset PINs to default (phone last 4 digits)"""
        from django.contrib.auth.hashers import make_password
        for account in queryset:
            default_pin = account.phone[-4:] if len(account.phone) >= 4 else '1234'
            account.pin_hash = make_password(default_pin)
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


# Register existing worker dispatch models if not already registered
try:
    admin.site.register(WorkSite)
except admin.sites.AlreadyRegistered:
    pass

try:
    admin.site.register(ClientAvailability)
except admin.sites.AlreadyRegistered:
    pass

try:
    admin.site.register(WorkAssignment)
except admin.sites.AlreadyRegistered:
    pass

try:
    admin.site.register(CallOutLog)
except admin.sites.AlreadyRegistered:
    pass
