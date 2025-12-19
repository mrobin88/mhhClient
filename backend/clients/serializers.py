from rest_framework import serializers
from .models import Client, CaseNote, PitStopApplication

class ClientSerializer(serializers.ModelSerializer):
    age = serializers.ReadOnlyField()
    full_name = serializers.ReadOnlyField()
    is_sf_resident = serializers.ReadOnlyField()
    has_resume = serializers.ReadOnlyField()
    case_notes_count = serializers.ReadOnlyField()
    
    class Meta:
        model = Client
        fields = '__all__'

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
