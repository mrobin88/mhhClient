from django.db import models
from django.urls import reverse
from django.contrib.auth import get_user_model
import logging

User = get_user_model()

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
        ('american_indian', 'American Indian or Alaska Native'),
        ('asian', 'Asian'),
        ('black', 'Black or African American'),
        ('white', 'Caucasian or White'),
        ('hispanic_latinx', 'Hispanic or Latin X'),
        ('middle_eastern', 'Middle Eastern'),
        ('pacific_islander', 'Native Hawaiian or Other Pacific Islander'),
        ('other', 'Other'),
        ('decline_state', 'Decline to State'),
        ('multiracial', 'Multiracial'),
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
    dob = models.DateField(blank=True, null=True)
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
    resume = models.FileField(upload_to='resumes/', blank=True, null=True, help_text='Upload client resume')
    
    # Status & Tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    staff_name = models.CharField(max_length=100, blank=True, null=True)
    
    # Program Completion & Job Placement Tracking
    program_start_date = models.DateField(blank=True, null=True, help_text="Date when client started their program")
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
        if not self.dob:
            return None
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
    
    def generate_resume_sas_url(self, expiry_minutes=15):
        """Generate a signed Azure SAS URL for resume download.
        Raises FileNotFoundError if blob is missing from Azure.
        """
        if not self.resume:
            return None
        from .storage import generate_document_sas_url
        return generate_document_sas_url(self.resume.name, expiry_minutes=expiry_minutes)
    
    @property
    def resume_download_url(self):
        """Generate secure download URL for resume. Returns None if file missing."""
        if not self.resume:
            return None
        try:
            return self.generate_resume_sas_url()
        except FileNotFoundError:
            return None
        except Exception as exc:
            logging.getLogger('clients').error('SAS failed for Client %s resume: %s', self.pk, exc)
            return None
    
    def get_resume_file_type(self):
        """Determine file type for preview purposes."""
        if not self.resume:
            return None
        filename = self.resume.name.lower()
        if filename.endswith('.pdf'):
            return 'pdf'
        elif any(filename.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
            return 'image'
        elif filename.endswith('.doc') or filename.endswith('.docx'):
            return 'word'
        else:
            return 'other'


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
        ('sf_residency', 'Proof of SF Residency'),
        ('hs_diploma', 'High School Diploma / GED'),
        ('id', 'Government ID'),
        ('photo_release', 'Photo Release Form'),
        ('employment_proof', 'Proof of Employment'),
        ('self_attestation', 'Employment Self-Attestation'),
        ('intake', 'Intake Form'),
        ('consent', 'Consent Form'),
        ('certificate', 'Certificate/Credential'),
        ('reference', 'Reference Letter'),
        ('other', 'Other Document'),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=255, help_text='Document title or description')
    doc_type = models.CharField(max_length=20, choices=DOC_TYPE_CHOICES, default='other')
    file = models.FileField(upload_to='documents/', help_text='Upload document file')

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
        """Auto-populate file metadata on save and verify upload."""
        is_new_file = False
        try:
            if self.file:
                self.file_size = self.file.size
                self.content_type = getattr(self.file.file, 'content_type', None)
                is_new_file = True
        except Exception:
            pass
        super().save(*args, **kwargs)

        if is_new_file and self.file:
            try:
                from .storage import verify_upload
                if verify_upload(self.file.name):
                    logging.getLogger('clients').info(
                        'Document %s uploaded and verified in Azure: %s', self.pk, self.file.name
                    )
                else:
                    logging.getLogger('clients').warning(
                        'Document %s saved but blob NOT found in Azure: %s', self.pk, self.file.name
                    )
            except Exception as exc:
                logging.getLogger('clients').warning(
                    'Document %s upload verification skipped: %s', self.pk, exc
                )

    def generate_sas_download_url(self, expiry_minutes=15):
        """Generate a signed Azure SAS URL for direct download."""
        if not self.file:
            return None
        from .storage import generate_document_sas_url
        return generate_document_sas_url(self.file.name, expiry_minutes=expiry_minutes)

    @property
    def blob_missing(self):
        """Check if the file is missing from Azure Storage."""
        if not self.file:
            return True
        try:
            from .storage import blob_exists
            return blob_exists(self.file.name) is None
        except Exception:
            return True

    @property
    def file_size_mb(self):
        """Return file size in MB"""
        if self.file_size:
            return round(self.file_size / (1024 * 1024), 2)
        return 0

    @property
    def download_url(self):
        """Generate secure download URL. Returns API fallback route if SAS fails."""
        if not self.file:
            return None
        try:
            return self.generate_sas_download_url()
        except FileNotFoundError:
            return None
        except Exception:
            return reverse('document-download', kwargs={'pk': self.pk})
    
    def get_file_type(self):
        """Determine file type for preview purposes."""
        if not self.file:
            return None
        filename = self.file.name.lower()
        if filename.endswith('.pdf'):
            return 'pdf'
        elif any(filename.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
            return 'image'
        elif filename.endswith('.doc') or filename.endswith('.docx'):
            return 'word'
        else:
            return 'other'


class PitStopApplication(models.Model):
    """Application details for the Pit Stop Program"""

    # Employment type choices (stored as JSONField array in employment_desired)
    EMPLOYMENT_DESIRED_CHOICES = [
        ('full_time', 'Full-time'),
        ('part_time', 'Part-time'),
        ('relief_list', 'Relief List'),
    ]
    
    # Shift time slots used in weekly_schedule JSONField
    # Frontend uses: '7-4', '8-5', '9-6', '10-7', '11-8', '12-9', '18-3', '21-6', '23-8'

    # Link to client
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='pitstop_applications')

    # Legal + veteran
    can_work_us = models.BooleanField(default=False)
    is_veteran = models.BooleanField(default=False)

    # Position and start
    position_applied_for = models.CharField(max_length=100)
    available_start_date = models.DateField(blank=True, null=True)
    employment_desired = models.JSONField(
        default=list,
        help_text='Employment types desired: ["full_time", "part_time", "relief_list"] - can select multiple'
    )

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


class JobPlacement(models.Model):
    """Tracks client job placement outcomes and who logged them."""

    WORK_TYPE_CHOICES = [
        ('full_time', 'Full-time'),
        ('part_time', 'Part-time'),
        ('contract', 'Contract'),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='job_placements')
    employer = models.CharField(max_length=150)
    work_type = models.CharField(max_length=20, choices=WORK_TYPE_CHOICES)
    job_title = models.CharField(max_length=120, blank=True, null=True)
    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    start_date = models.DateField()
    employer_address = models.CharField(max_length=255, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    created_by_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='logged_job_placements',
    )
    created_by_name = models.CharField(max_length=100, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date', '-created_at']
        verbose_name = 'Job Placement'
        verbose_name_plural = 'Job Placements'

    def __str__(self):
        return f"{self.client.full_name} @ {self.employer} ({self.start_date})"


# Import extended models for worker dispatch system
from .models_extensions import WorkSite, WorkAssignment, OpenShift, ShiftCoverInterest
