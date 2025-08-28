from rest_framework import serializers
from .models import Client, CaseNote

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
    
    class Meta:
        model = CaseNote
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
