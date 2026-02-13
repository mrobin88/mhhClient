from rest_framework import serializers
from .models import Client, CaseNote, PitStopApplication
from .models_extensions import WorkerAccount, ServiceRequest, WorkAssignment, ClientAvailability, WorkSite

class ClientSerializer(serializers.ModelSerializer):
    age = serializers.ReadOnlyField()
    full_name = serializers.ReadOnlyField()
    is_sf_resident = serializers.ReadOnlyField()
    has_resume = serializers.ReadOnlyField()
    case_notes_count = serializers.ReadOnlyField()
    resume_download_url = serializers.SerializerMethodField()
    resume_file_type = serializers.SerializerMethodField()
    
    class Meta:
        model = Client
        fields = '__all__'
    
    def get_resume_download_url(self, obj):
        """Generate secure SAS URL for resume download"""
        if not obj.resume:
            return None
        try:
            return obj.resume_download_url
        except Exception as e:
            # Log error but don't fail serialization
            import logging
            logging.getLogger('clients').error(
                'Failed to generate resume download URL for Client %s: %s', 
                obj.pk, e
            )
            return None
    
    def get_resume_file_type(self, obj):
        """Get file type for preview purposes"""
        if not obj.resume:
            return None
        return obj.get_resume_file_type()

class CaseNoteSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.full_name', read_only=True)
    formatted_timestamp = serializers.SerializerMethodField()
    formatted_date = serializers.SerializerMethodField()
    relative_time = serializers.SerializerMethodField()
    note_type_display = serializers.CharField(source='get_note_type_display', read_only=True)
    
    class Meta:
        model = CaseNote
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'formatted_timestamp', 'formatted_date', 'relative_time', 'note_type_display']
    
    def get_formatted_timestamp(self, obj):
        """Return formatted timestamp: Jan 15, 2025 at 2:30 PM"""
        if not obj.created_at:
            return None
        return obj.created_at.strftime('%b %d, %Y at %I:%M %p')
    
    def get_formatted_date(self, obj):
        """Return formatted date: Jan 15, 2025"""
        if not obj.created_at:
            return None
        return obj.created_at.strftime('%b %d, %Y')
    
    def get_relative_time(self, obj):
        """Return relative time: 2 hours ago, 3 days ago, etc."""
        if not obj.created_at:
            return None
        
        from django.utils import timezone
        now = timezone.now()
        
        # Handle both timezone-aware and naive datetimes
        if obj.created_at.tzinfo:
            diff = now - obj.created_at
        else:
            diff = timezone.make_aware(now) - timezone.make_aware(obj.created_at)
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds >= 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.seconds >= 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "just now"


class PitStopApplicationSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.full_name', read_only=True)

    class Meta:
        model = PitStopApplication
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


# ========================================
# Worker Portal Serializers
# ========================================

class WorkerLoginSerializer(serializers.Serializer):
    """Serializer for worker authentication with phone + PIN"""
    phone = serializers.CharField(max_length=20)
    pin = serializers.CharField(max_length=6, write_only=True)
    
    def validate(self, data):
        """Validate phone and PIN combination"""
        phone = data.get('phone')
        pin = data.get('pin')
        
        try:
            worker_account = WorkerAccount.objects.select_related('client').get(phone=phone)
        except WorkerAccount.DoesNotExist:
            raise serializers.ValidationError('Invalid phone number or PIN')
        
        # Check if account is locked
        if worker_account.is_locked:
            raise serializers.ValidationError('Account is temporarily locked. Please try again later.')
        
        # Check if account is active and approved
        if not worker_account.is_active:
            raise serializers.ValidationError('Account is not active. Please contact your supervisor.')
        
        if not worker_account.is_approved:
            raise serializers.ValidationError('Account is pending approval. Please contact your supervisor.')
        
        # Check PIN
        if not worker_account.check_pin(pin):
            worker_account.increment_login_attempts()
            raise serializers.ValidationError('Invalid phone number or PIN')
        
        # Reset login attempts on successful validation
        worker_account.reset_login_attempts()
        
        data['worker_account'] = worker_account
        return data


class WorkerAccountSerializer(serializers.ModelSerializer):
    """Serializer for worker account information"""
    client_name = serializers.CharField(source='client.full_name', read_only=True)
    client_phone = serializers.CharField(source='client.phone', read_only=True)
    client_email = serializers.CharField(source='client.email', read_only=True)
    
    class Meta:
        model = WorkerAccount
        fields = ['id', 'client', 'client_name', 'client_phone', 'client_email', 'phone', 'is_active', 'last_login']
        read_only_fields = ['id', 'last_login']


class WorkSiteSerializer(serializers.ModelSerializer):
    """Serializer for work site information"""
    
    class Meta:
        model = WorkSite
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class WorkAssignmentSerializer(serializers.ModelSerializer):
    """Serializer for work assignments"""
    client_name = serializers.CharField(source='client.full_name', read_only=True)
    work_site_name = serializers.CharField(source='work_site.name', read_only=True)
    work_site_address = serializers.CharField(source='work_site.address', read_only=True)
    work_site_supervisor = serializers.CharField(source='work_site.supervisor_name', read_only=True)
    work_site_supervisor_phone = serializers.CharField(source='work_site.supervisor_phone', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_today = serializers.ReadOnlyField()
    is_upcoming = serializers.ReadOnlyField()
    
    class Meta:
        model = WorkAssignment
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'assigned_by']


class WorkerAssignmentSerializer(serializers.ModelSerializer):
    """Simplified serializer for worker's own assignments"""
    work_site_name = serializers.CharField(source='work_site.name', read_only=True)
    work_site_address = serializers.CharField(source='work_site.address', read_only=True)
    work_site_supervisor = serializers.CharField(source='work_site.supervisor_name', read_only=True)
    work_site_supervisor_phone = serializers.CharField(source='work_site.supervisor_phone', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = WorkAssignment
        fields = [
            'id', 'assignment_date', 'start_time', 'end_time', 
            'work_site_name', 'work_site_address', 
            'work_site_supervisor', 'work_site_supervisor_phone',
            'status', 'status_display', 'confirmed_by_client', 'assignment_notes'
        ]
        read_only_fields = ['assignment_date', 'start_time', 'end_time', 'assignment_notes']


class CallOutSerializer(serializers.Serializer):
    """Serializer for workers to submit call-outs"""
    assignment_id = serializers.IntegerField()
    reason = serializers.CharField(max_length=500)
    advance_notice_hours = serializers.IntegerField(min_value=0, max_value=72)
    
    def validate_assignment_id(self, value):
        """Validate that assignment exists and belongs to the worker"""
        try:
            assignment = WorkAssignment.objects.get(id=value)
            # Additional validation will be done in the view
            return value
        except WorkAssignment.DoesNotExist:
            raise serializers.ValidationError('Assignment not found')


class ClientAvailabilitySerializer(serializers.ModelSerializer):
    """Serializer for client availability"""
    day_display = serializers.CharField(source='get_day_of_week_display', read_only=True)
    
    class Meta:
        model = ClientAvailability
        fields = '__all__'
        read_only_fields = ['client']


class ServiceRequestSerializer(serializers.ModelSerializer):
    """Serializer for service requests"""
    submitted_by_name = serializers.CharField(source='submitted_by.full_name', read_only=True)
    work_site_name = serializers.CharField(source='work_site.name', read_only=True)
    issue_type_display = serializers.CharField(source='get_issue_type_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_overdue = serializers.ReadOnlyField()
    
    class Meta:
        model = ServiceRequest
        fields = '__all__'
        read_only_fields = [
            'submitted_by', 'created_at', 'updated_at',
            'acknowledged_by', 'acknowledged_at', 'resolved_at'
        ]


class WorkerServiceRequestSerializer(serializers.ModelSerializer):
    """Simplified serializer for workers to submit service requests"""
    
    class Meta:
        model = ServiceRequest
        fields = [
            'work_site', 'issue_type', 'title', 'description',
            'location_detail', 'priority', 'photo'
        ]
