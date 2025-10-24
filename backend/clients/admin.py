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
from .models import Client, CaseNote, Document, PitStopApplication

# Try to import WeasyPrint for PDF generation
try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError):
    WEASYPRINT_AVAILABLE = False

@admin.register(CaseNote)
class CaseNoteAdmin(admin.ModelAdmin):
    list_display = ['client', 'note_type', 'staff_member', 'created_at', 'follow_up_date', 'is_overdue']
    list_filter = ['note_type', 'staff_member', 'created_at', 'follow_up_date']
    search_fields = ['client__first_name', 'client__last_name', 'content', 'staff_member']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Client Information', {
            'fields': ('client', 'staff_member')
        }),
        ('Note Details', {
            'fields': ('note_type', 'content', 'next_steps')
        }),
        ('Follow-up', {
            'fields': ('follow_up_date',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def is_overdue(self, obj):
        if obj.is_overdue_followup:
            return format_html('<span style="color: red; font-weight: bold;">OVERDUE</span>')
        return format_html('<span style="color: green;">On Track</span>')
    is_overdue.short_description = 'Follow-up Status'

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'phone', 'email', 'training_interest', 'status', 'job_placed', 'program_completed_date', 'has_resume', 'case_notes_count', 'created_at']
    list_filter = ['status', 'training_interest', 'job_placed', 'neighborhood', 'sf_resident', 'employment_status', 'created_at', 'program_completed_date']
    search_fields = ['first_name', 'last_name', 'phone', 'job_title', 'job_company']
    readonly_fields = ['created_at', 'updated_at', 'case_notes_count', 'masked_ssn']
    date_hierarchy = 'created_at'
    
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
        """Export client profiles as PDF documents"""
        if not WEASYPRINT_AVAILABLE:
            self.message_user(request, 'PDF generation is not available. WeasyPrint is not installed.', level='error')
            return
        
        if queryset.count() > 10:
            self.message_user(request, 'Please select 10 or fewer clients for PDF export to avoid timeout.', level='warning')
            return
        
        try:
            # Create a combined PDF with all selected client profiles
            combined_html = ""
            
            for client in queryset.prefetch_related('casenotes'):
                case_notes = client.casenotes.all()[:5]  # Latest 5 case notes
                
                html_content = render_to_string('admin/clients/client_profile.html', {
                    'client': client,
                    'case_notes': case_notes,
                    'generated_at': datetime.now()
                })
                
                combined_html += html_content + '<div style="page-break-after: always;"></div>'
            
            # Generate PDF
            pdf_buffer = io.BytesIO()
            HTML(string=combined_html).write_pdf(pdf_buffer)
            pdf_buffer.seek(0)
            
            response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
            filename = f"client_profiles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            return response
            
        except Exception as e:
            self.message_user(request, f'PDF generation failed: {str(e)}', level='error')
    
    export_client_profiles_pdf.short_description = "Export client profiles as PDF"

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
