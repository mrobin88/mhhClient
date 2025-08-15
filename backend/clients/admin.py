from django.contrib import admin
from django.utils.html import format_html
from .models import Client

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = (
        'full_name', 
        'phone', 
        'neighborhood', 
        'training_interest', 
        'status', 
        'staff_name', 
        'created_at',
        'sf_resident_display'
    )
    
    list_filter = (
        'status',
        'training_interest', 
        'neighborhood',
        'sf_resident',
        'demographic_info', 
        'language', 
        'gender', 
        'employment_status',
        'staff_name',
        'created_at'
    )
    
    search_fields = (
        'first_name', 
        'last_name', 
        'phone', 
        'ssn', 
        'staff_name',
        'neighborhood'
    )
    
    readonly_fields = ('created_at', 'updated_at', 'age_display')
    
    fieldsets = (
        ('Personal Information', {
            'fields': (
                'first_name', 
                'last_name', 
                'dob', 
                'ssn', 
                'phone', 
                'gender'
            )
        }),
        ('San Francisco Residency & Background', {
            'fields': (
                'sf_resident',
                'neighborhood',
                'demographic_info', 
                'language', 
                'language_other',
                'highest_degree'
            )
        }),
        ('Employment & Training', {
            'fields': (
                'employment_status',
                'training_interest',
                'referral_source',
                'additional_notes'
            )
        }),
        ('Status & Tracking', {
            'fields': (
                'status',
                'staff_name',
                'created_at',
                'updated_at'
            )
        }),
    )
    
    list_per_page = 50
    
    actions = ['mark_active', 'mark_completed', 'mark_pending', 'mark_inactive']
    
    def full_name(self, obj):
        return obj.full_name
    full_name.short_description = 'Full Name'
    full_name.admin_order_field = 'first_name'
    
    def sf_resident_display(self, obj):
        if obj.sf_resident == 'yes':
            return format_html('<span style="color: green;">✓ SF Resident</span>')
        else:
            return format_html('<span style="color: red;">✗ Non-SF</span>')
    sf_resident_display.short_description = 'SF Resident'
    
    def age_display(self, obj):
        return f"{obj.age} years old"
    age_display.short_description = 'Age'
    
    def mark_active(self, request, queryset):
        updated = queryset.update(status='active')
        self.message_user(request, f'{updated} clients marked as active.')
    mark_active.short_description = "Mark selected clients as active"
    
    def mark_completed(self, request, queryset):
        updated = queryset.update(status='completed')
        self.message_user(request, f'{updated} clients marked as completed.')
    mark_completed.short_description = "Mark selected clients as completed"
    
    def mark_pending(self, request, queryset):
        updated = queryset.update(status='pending')
        self.message_user(request, f'{updated} clients marked as pending.')
    mark_pending.short_description = "Mark selected clients as pending"
    
    def mark_inactive(self, request, queryset):
        updated = queryset.update(status='inactive')
        self.message_user(request, f'{updated} clients marked as inactive.')
    mark_inactive.short_description = "Mark selected clients as inactive"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related()
    
    def get_list_display(self, request):
        """Customize list display based on user permissions"""
        if request.user.is_superuser:
            return self.list_display
        else:
            # Staff users see a simplified view
            return (
                'full_name', 
                'phone', 
                'neighborhood', 
                'training_interest', 
                'status', 
                'created_at'
            )
    
    def has_delete_permission(self, request, obj=None):
        """Only superusers can delete clients"""
        return request.user.is_superuser
    
    def has_change_permission(self, request, obj=None):
        """Staff can edit clients"""
        return True
    
    def has_add_permission(self, request):
        """Staff can add new clients"""
        return True
