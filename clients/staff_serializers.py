"""Staff SPA serializers — no full SSN, focused list/detail fields."""
from rest_framework import serializers

from .models import Client, CaseNote


class StaffClientListSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    training_interest_display = serializers.CharField(
        source='get_training_interest_display', read_only=True
    )
    pit_stop_stage_display = serializers.CharField(
        source='get_pit_stop_stage_display', read_only=True
    )

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
            'training_interest',
            'training_interest_display',
            'pit_stop_stage',
            'pit_stop_stage_display',
            'updated_at',
        ]


class StaffClientDetailSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    age = serializers.ReadOnlyField()
    case_notes_count = serializers.ReadOnlyField()
    training_interest_display = serializers.CharField(
        source='get_training_interest_display', read_only=True
    )
    pit_stop_stage_display = serializers.CharField(
        source='get_pit_stop_stage_display', read_only=True
    )
    worker_portal = serializers.SerializerMethodField()
    pit_stop_application = serializers.SerializerMethodField()

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
            'neighborhood_other',
            'demographic_info',
            'language',
            'employment_status',
            'training_interest',
            'training_interest_display',
            'pit_stop_stage',
            'pit_stop_stage_display',
            'pit_stop_application',
            'worker_portal',
            'program_start_date',
            'program_completed_date',
            'age',
            'case_notes_count',
            'created_at',
            'updated_at',
        ]

    def get_worker_portal(self, obj):
        """Summary so staff can check portal access without opening Django admin."""
        account = getattr(obj, 'worker_account', None)
        if account is None:
            return None

        last_punch = account.time_punches.order_by('-clock_in_at').first()
        return {
            'has_account': True,
            'login_phone': account.phone,
            'portal_access': account.is_active,
            'worker_status': account.worker_status,
            'worker_status_display': account.get_worker_status_display(),
            'last_login': account.last_login,
            'last_clock_in': getattr(last_punch, 'clock_in_at', None),
        }

    def get_pit_stop_application(self, obj):
        app = obj.pitstop_applications.order_by('-created_at').first()
        if app is None:
            return None
        return {
            'id': app.pk,
            'review_status': app.review_status,
            'review_status_display': app.get_review_status_display(),
            'interviewed_on': app.interviewed_on,
            'review_notes': app.review_notes,
            'reviewed_by': app.reviewed_by,
            'review_updated_at': app.review_updated_at,
            'age': app.applicant_age,
            'area_code': app.area_code,
            'has_resume': app.has_resume,
            'position_applied_for': app.position_applied_for,
            'employment_desired': app.employment_desired,
            'available_start_date': app.available_start_date,
            'available_days': app.available_days_list,
            'can_work_us': app.can_work_us,
            'is_veteran': app.is_veteran,
            'education_history': app.education_history,
            'created_at': app.created_at,
        }


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
