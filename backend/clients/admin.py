from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Client, CaseNote

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
    list_display = ['full_name', 'phone', 'neighborhood', 'training_interest', 'status', 'has_resume', 'case_notes_count', 'created_at']
    list_filter = ['status', 'training_interest', 'neighborhood', 'sf_resident', 'employment_status', 'created_at']
    search_fields = ['first_name', 'last_name', 'phone', 'ssn']
    readonly_fields = ['created_at', 'updated_at', 'case_notes_count']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'dob', 'ssn', 'phone', 'gender')
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
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('casenotes')
    
    actions = ['mark_active', 'mark_completed', 'export_to_csv']
    
    def mark_active(self, request, queryset):
        updated = queryset.update(status='active')
        self.message_user(request, f'{updated} clients marked as active.')
    mark_active.short_description = "Mark selected clients as active"
    
    def mark_completed(self, request, queryset):
        updated = queryset.update(status='completed')
        self.message_user(request, f'{updated} clients marked as completed.')
    mark_completed.short_description = "Mark selected clients as completed"
