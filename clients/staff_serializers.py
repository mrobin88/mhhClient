"""Staff SPA serializers — no full SSN, focused list/detail fields."""
from rest_framework import serializers

from .models import Client, CaseNote


class StaffClientListSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = Client
        fields = [
            'id',
            'full_name',
            'first_name',
            'last_name',
            'phone',
            'email',
            'status',
            'staff_name',
            'neighborhood',
            'updated_at',
        ]


class StaffClientDetailSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    age = serializers.ReadOnlyField()
    case_notes_count = serializers.ReadOnlyField()

    class Meta:
        model = Client
        fields = [
            'id',
            'full_name',
            'first_name',
            'middle_name',
            'last_name',
            'dob',
            'phone',
            'email',
            'gender',
            'address',
            'city',
            'state',
            'zip_code',
            'status',
            'staff_name',
            'sf_resident',
            'neighborhood',
            'demographic_info',
            'language',
            'employment_status',
            'training_interest',
            'program_start_date',
            'program_completed_date',
            'age',
            'case_notes_count',
            'created_at',
            'updated_at',
        ]


class StaffCaseNoteSerializer(serializers.ModelSerializer):
    note_type_display = serializers.CharField(source='get_note_type_display', read_only=True)

    class Meta:
        model = CaseNote
        fields = [
            'id',
            'client',
            'note_date',
            'note_type',
            'note_type_display',
            'content',
            'next_steps',
            'staff_member',
            'created_at',
        ]
        read_only_fields = ['created_at', 'staff_member']
