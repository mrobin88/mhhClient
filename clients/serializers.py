from rest_framework import serializers
from .models import Client, CaseNote, PitStopApplication, JobPlacement
from .models_extensions import (
    WorkerAccount,
    WorkAssignment,
    WorkSite,
    WorkerTimePunch,
)
from .phone_utils import find_by_normalized_phone, phone_digits

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


class JobPlacementSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.full_name', read_only=True)

    class Meta:
        model = JobPlacement
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'created_by_user', 'created_by_name']


# ========================================
# Worker Portal Serializers
# ========================================

class WorkerLoginSerializer(serializers.Serializer):
    """Serializer for worker authentication with phone + PIN"""
    phone = serializers.CharField(max_length=20)
    pin = serializers.CharField(max_length=6, write_only=True)
    
    def validate(self, data):
        """Validate phone and PIN combination (phone may be formatted in DB; PIN is digits-only)."""
        phone = data.get('phone')
        pin = phone_digits(data.get('pin') or '')
        if len(pin) < 4:
            raise serializers.ValidationError({'pin': ['Enter a 4-digit PIN.']})
        if len(pin) > 6:
            pin = pin[:6]

        worker_account = find_by_normalized_phone(
            WorkerAccount.objects.select_related('client'),
            phone,
        )
        if not worker_account:
            raise serializers.ValidationError('Invalid phone number or PIN')

        if worker_account.is_locked:
            raise serializers.ValidationError('Account is temporarily locked. Please try again later.')

        if not worker_account.is_active:
            raise serializers.ValidationError('Portal access is turned off. Ask your supervisor to enable it.')

        if not worker_account.check_pin(pin):
            worker_account.increment_login_attempts()
            raise serializers.ValidationError('Invalid phone number or PIN')

        worker_account.reset_login_attempts()

        data['worker_account'] = worker_account
        return data


class WorkerAccountSerializer(serializers.ModelSerializer):
    """Serializer for worker account information"""
    client_name = serializers.CharField(source='client.full_name', read_only=True)
    client_phone = serializers.CharField(source='client.phone', read_only=True)
    client_email = serializers.CharField(source='client.email', read_only=True)
    worker_status_label = serializers.CharField(source='get_worker_status_display', read_only=True)
    
    class Meta:
        model = WorkerAccount
        fields = [
            'id',
            'client',
            'client_name',
            'client_phone',
            'client_email',
            'phone',
            'is_active',
            'worker_status',
            'worker_status_label',
            'is_available',
            'last_login',
        ]
        read_only_fields = ['id', 'last_login']


class WorkSiteSerializer(serializers.ModelSerializer):
    """Serializer for work site information"""
    
    class Meta:
        model = WorkSite
        fields = [
            'id',
            'name',
            'address',
            'neighborhood',
            'latitude',
            'longitude',
            'is_active',
        ]
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
    location_display = serializers.SerializerMethodField()
    
    class Meta:
        model = WorkAssignment
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'assigned_by']

    def get_location_display(self, obj):
        if not obj.work_site:
            return 'Location to be confirmed'
        parts = [obj.work_site.name]
        if obj.work_site.address:
            parts.append(obj.work_site.address)
        return ' - '.join(parts)


class WorkerTimePunchSerializer(serializers.ModelSerializer):
    """Worker-facing clock in/out record."""

    is_open = serializers.SerializerMethodField()
    duration_minutes = serializers.SerializerMethodField()
    assignment_label = serializers.SerializerMethodField()
    work_site_name = serializers.CharField(source='work_site.name', read_only=True)

    class Meta:
        model = WorkerTimePunch
        fields = [
            'id',
            'assignment',
            'assignment_label',
            'work_site',
            'work_site_name',
            'clock_in_at',
            'clock_out_at',
            'clock_in_server_received_at',
            'clock_out_server_received_at',
            'clock_in_geo_basic_ok',
            'clock_in_geo_basic_note',
            'clock_out_geo_basic_ok',
            'clock_out_geo_basic_note',
            'is_open',
            'duration_minutes',
        ]

    def get_is_open(self, obj):
        return obj.clock_out_at is None

    def get_duration_minutes(self, obj):
        if obj.clock_out_at is None:
            return None
        duration_seconds = (obj.clock_out_at - obj.clock_in_at).total_seconds()
        return int(max(duration_seconds, 0) // 60)

    def get_assignment_label(self, obj):
        assignment = getattr(obj, 'assignment', None)
        if assignment:
            site_name = assignment.work_site.name if getattr(assignment, 'work_site', None) else 'Work site'
            return f'{assignment.assignment_date} {assignment.start_time} - {site_name}'
        if obj.work_site:
            return obj.work_site.name
        return ''


