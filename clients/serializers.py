from rest_framework import serializers
from .models import Client, CaseNote, PitStopApplication, JobPlacement
from .models_extensions import (
    WorkerAccount,
    ServiceRequest,
    WorkAssignment,
    WorkSite,
    OpenShift,
    ShiftCoverInterest,
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


class OpenShiftSerializer(serializers.ModelSerializer):
    """Open shift listing for workers."""

    location_display = serializers.SerializerMethodField()
    work_site_name = serializers.CharField(
        source='work_site.name', read_only=True, allow_null=True
    )

    class Meta:
        model = OpenShift
        fields = [
            'id',
            'role_title',
            'location_display',
            'work_site_name',
            'shift_date',
            'start_time',
            'end_time',
            'notes',
        ]

    def get_location_display(self, obj):
        if obj.work_site:
            parts = [obj.work_site.name]
            if getattr(obj.work_site, 'address', None):
                parts.append(obj.work_site.address)
            return ' — '.join(parts)
        return obj.location_label or 'Location to be confirmed'


class ShiftCoverInterestSerializer(serializers.ModelSerializer):
    """Worker-facing interest record."""

    open_shift = OpenShiftSerializer(read_only=True)
    message_for_worker = serializers.SerializerMethodField()

    class Meta:
        model = ShiftCoverInterest
        fields = [
            'id',
            'open_shift',
            'status',
            'message_for_worker',
            'created_at',
        ]

    def get_message_for_worker(self, obj):
        if obj.status == ShiftCoverInterest.STATUS_PENDING:
            return (
                'Thanks — we noted your interest. A supervisor may reach out if you are picked for this shift.'
            )
        if obj.status == ShiftCoverInterest.STATUS_SELECTED:
            return 'You were selected for this shift. Watch for a call or message from the team.'
        if obj.status == ShiftCoverInterest.STATUS_NOT_SELECTED:
            return 'This shift was filled another way. Thank you for offering to help.'
        if obj.status == ShiftCoverInterest.STATUS_CANCELLED:
            return 'This shift is no longer open.'
        return ''


class ShiftCoverInterestStaffSerializer(serializers.ModelSerializer):
    """Staff PATCH: status and internal note."""

    class Meta:
        model = ShiftCoverInterest
        fields = ['status', 'staff_note']


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


