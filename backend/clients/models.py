from django.db import models
from django.core.files.storage import default_storage

# Import extended models at the end of file to avoid circular imports
from django.urls import reverse

class Client(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'), 
        ('F', 'Female'), 
        ('NB', 'Non-binary'), 
        ('O', 'Other'),
        ('P', 'Prefer not to say')
    ]
    
    LANGUAGE_CHOICES = [
        ('en', 'English'), 
        ('es', 'Spanish'), 
        ('zh', 'Chinese (Mandarin/Cantonese)'),
        ('vi', 'Vietnamese'),
        ('tl', 'Tagalog/Filipino'),
        ('other', 'Other')
    ]
    
    DEMOGRAPHIC_CHOICES = [
        ('black', 'Black/African American'), 
        ('white', 'White/Caucasian'), 
        ('latinx', 'Hispanic/Latinx'), 
        ('asian', 'Asian/Pacific Islander'), 
        ('native', 'Native American'),
        ('mixed', 'Mixed Race'),
        ('other', 'Other'),
        ('prefer_not', 'Prefer not to say')
    ]
    
    EDUCATION_CHOICES = [
        ('none', 'No formal education'),
        ('elementary', 'Elementary school'),
        ('middle', 'Middle school'),
        ('hs', 'High school diploma/GED'),
        ('some_college', 'Some college'),
        ('aa', 'Associate\'s degree (AA)'),
        ('ba', 'Bachelor\'s degree (BA/BS)'),
        ('ma', 'Master\'s degree (MA/MS)'),
        ('phd', 'Doctorate (PhD)')
    ]
    
    EMPLOYMENT_STATUS_CHOICES = [
        ('unemployed', 'Unemployed'),
        ('part_time', 'Part-time employment'),
        ('full_time', 'Full-time employment'),
        ('underemployed', 'Underemployed (seeking better job)'),
        ('student', 'Student'),
        ('other', 'Other')
    ]
    
    TRAINING_INTEREST_CHOICES = [
        ('citybuild', 'CityBuild Academy'),
        ('citybuild_pro', 'CityBuild Pro | CAPSA'),
        ('security', 'Security Guard Card Program'),
        ('construction', 'Construction On Ramp'),
        ('pit_stop', 'Pit Stop Program'),
        ('general', 'General job readiness'),
        ('other', 'Other training')
    ]
    
    NEIGHBORHOOD_CHOICES = [
        ('mission', 'Mission District'),
        ('soma', 'South of Market (SoMa)'),
        ('bayview', 'Bayview-Hunters Point'),
        ('tenderloin', 'Tenderloin'),
        ('western', 'Western Addition'),
        ('other', 'Other San Francisco Area')
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('inactive', 'Inactive')
    ]

    # Personal Information
    first_name = models.CharField(max_length=50)
    middle_name = models.CharField(max_length=50, blank=True, null=True)
    last_name = models.CharField(max_length=50)
    dob = models.DateField()
    ssn = models.CharField(max_length=11, blank=True, null=True)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)

    # Address
    address = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=50, blank=True, null=True)
    zip_code = models.CharField(max_length=20, blank=True, null=True)
    
    # San Francisco Residency & Background
    sf_resident = models.CharField(max_length=10, choices=[('yes', 'Yes'), ('no', 'No')], default='yes')
    neighborhood = models.CharField(max_length=20, choices=NEIGHBORHOOD_CHOICES, default='other')
    demographic_info = models.CharField(max_length=20, choices=DEMOGRAPHIC_CHOICES, default='other')
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default='en')
    language_other = models.CharField(max_length=50, blank=True, null=True)
    highest_degree = models.CharField(max_length=20, choices=EDUCATION_CHOICES, default='none')
    
    # Employment & Training
    employment_status = models.CharField(max_length=20, choices=EMPLOYMENT_STATUS_CHOICES, default='unemployed')
    training_interest = models.CharField(max_length=20, choices=TRAINING_INTEREST_CHOICES, default='general')
    referral_source = models.CharField(max_length=20, choices=[
        ('friend', 'Friend or family member'),
        ('social_media', 'Social media'),
        ('website', 'Website search'),
        ('job_center', 'Job center/Workforce development'),
        ('community_org', 'Community organization'),
        ('walk_in', 'Walk-in visit'),
        ('other', 'Other')
    ], default='other')
    additional_notes = models.TextField(blank=True, null=True)
    
    # Resume & Documents
    resume = models.FileField(upload_to='client-docs/resumes/', blank=True, null=True, help_text='Upload client resume')
    
    # Status & Tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    staff_name = models.CharField(max_length=100, blank=True, null=True)
    
    # Program Completion & Job Placement Tracking
    program_completed_date = models.DateField(blank=True, null=True, help_text="Date when client completed their program")
    job_placed = models.BooleanField(default=False, help_text="Was client placed in a job after program completion?")
    job_placement_date = models.DateField(blank=True, null=True, help_text="Date when client was placed in job")
    job_title = models.CharField(max_length=100, blank=True, null=True, help_text="Job title/position client was placed in")
    job_company = models.CharField(max_length=100, blank=True, null=True, help_text="Company where client was placed")
    job_hourly_wage = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True, help_text="Hourly wage for placed job")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Client'
        verbose_name_plural = 'Clients'

    def __str__(self):
        parts = [self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        parts.append(self.last_name)
        return " ".join(parts)
    
    @property
    def full_name(self):
        parts = [self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        parts.append(self.last_name)
        return " ".join(parts)
    
    @property
    def age(self):
        from datetime import date
        today = date.today()
        return today.year - self.dob.year - ((today.month, today.day) < (self.dob.month, self.dob.day))
    
    @property
    def is_sf_resident(self):
        return self.sf_resident == 'yes'
    
    @property
    def has_resume(self):
        return bool(self.resume)
    
    @property
    def case_notes_count(self):
        return self.casenotes.count()
    
    @property
    def documents_count(self):
        return self.documents.count()


class CaseNote(models.Model):
    """Case notes for tracking client interactions and progress"""
    
    NOTE_TYPE_CHOICES = [
        ('intake', 'Intake Meeting'),
        ('follow_up', 'Follow-up Call/Visit'),
        ('training', 'Training Progress'),
        ('job_search', 'Job Search Support'),
        ('placement', 'Job Placement'),
        ('barrier', 'Barrier Assessment'),
        ('referral', 'Referral to Service'),
        ('general', 'General Note')
    ]
    
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='casenotes')
    staff_member = models.CharField(max_length=100, help_text='Staff member who created this note')
    note_type = models.CharField(max_length=20, choices=NOTE_TYPE_CHOICES, default='general')
    content = models.TextField(help_text='Case note content')
    next_steps = models.TextField(blank=True, null=True, help_text='Next steps or action items')
    follow_up_date = models.DateField(blank=True, null=True, help_text='When to follow up')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Case Note'
        verbose_name_plural = 'Case Notes'
    
    def __str__(self):
        return f"{self.client.full_name} - {self.note_type} - {self.created_at.strftime('%m/%d/%Y')}"
    
    @property
    def is_overdue_followup(self):
        if not self.follow_up_date:
            return False
        from datetime import date
        return date.today() > self.follow_up_date


class Document(models.Model):
    """Client document storage with Azure Blob Storage integration"""

    DOC_TYPE_CHOICES = [
        ('resume', 'Resume'),
        ('intake', 'Intake Form'),
        ('consent', 'Consent Form'),
        ('id', 'Identification'),
        ('certificate', 'Certificate/Credential'),
        ('reference', 'Reference Letter'),
        ('other', 'Other Document'),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=255, help_text='Document title or description')
    doc_type = models.CharField(max_length=20, choices=DOC_TYPE_CHOICES, default='other')
    file = models.FileField(upload_to='client-docs/', help_text='Upload document file')

    # Metadata
    file_size = models.PositiveIntegerField(null=True, blank=True, help_text='File size in bytes')
    content_type = models.CharField(max_length=100, blank=True, null=True)
    uploaded_by = models.CharField(max_length=100, help_text='Staff member who uploaded this document')
    notes = models.TextField(blank=True, null=True, help_text='Additional notes about this document')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Document'
        verbose_name_plural = 'Documents'

    def __str__(self):
        return f"{self.client.full_name} - {self.title}"

    def save(self, *args, **kwargs):
        """Auto-populate file metadata on save; fail-soft if storage backend errors."""
        try:
            if self.file:
                self.file_size = self.file.size
                self.content_type = getattr(self.file.file, 'content_type', None)
        except Exception:
            # If storage backend is unreachable, skip metadata but still save DB row
            pass
        super().save(*args, **kwargs)

    def generate_sas_download_url(self, expiry_minutes=15):
        """Generate a signed Azure SAS URL for direct download."""
        # Public access: SAS not needed; use direct URL
        return self.file.url if self.file else None

    @property
    def file_size_mb(self):
        """Return file size in MB"""
        if self.file_size:
            return round(self.file_size / (1024 * 1024), 2)
        return 0

    @property
    def download_url(self):
        """Generate secure download URL (preferred SAS, fallback to API route)."""
        if not self.file:
            return None
        sas = self.generate_sas_download_url()
        if sas:
            return sas
        return reverse('document-download', kwargs={'pk': self.pk})


class PitStopApplication(models.Model):
    """Application details for the Pit Stop Program"""

    SHIFT_CHOICES = [
        ('6-12', '6am-12pm'),
        ('13-21', '1pm-9pm'),
        ('22-5', '10pm-5am'),
    ]

    EMPLOYMENT_DESIRED_CHOICES = [
        ('full_time', 'Full-time'),
        ('part_time', 'Part-time'),
        ('relief_list', 'Relief List'),
    ]

    # Link to client
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='pitstop_applications')

    # Legal + veteran
    can_work_us = models.BooleanField(default=False)
    is_veteran = models.BooleanField(default=False)

    # Position and start
    position_applied_for = models.CharField(max_length=100)
    available_start_date = models.DateField(blank=True, null=True)
    employment_desired = models.CharField(max_length=20, choices=EMPLOYMENT_DESIRED_CHOICES)

    # Weekly availability: store schedule for each day with time preferences
    weekly_schedule = models.JSONField(
        default=dict, 
        help_text='Weekly schedule: {"Mon": ["7-4", "8-5"], "Tue": ["9-5"], ...} - each day can have multiple time slots'
    )

    # Employment history (last job)
    employment_history = models.JSONField(default=list, help_text='Last job with fields: company, city, state, manager, phone, title, responsibilities, start_date, end_date')

    # Education history (free form)
    education_history = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Pit Stop Application'
        verbose_name_plural = 'Pit Stop Applications'

    def __str__(self):
        return f"PitStop Application - {self.client.full_name} - {self.position_applied_for}"
    
    @property
    def available_days_list(self):
        """Get list of days that have any time slots available"""
        if not self.weekly_schedule:
            return []
        return [day for day, times in self.weekly_schedule.items() if times]
    
    def get_times_for_day(self, day):
        """Get list of time slots for a specific day"""
        return self.weekly_schedule.get(day, [])


# Import extended models for worker dispatch system
from .models_extensions import WorkSite, ClientAvailability, WorkAssignment, CallOutLog
