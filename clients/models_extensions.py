"""
Extended models for worker dispatch and availability tracking
"""
from django.db import models
from django.core.exceptions import ValidationError
from .models import Client, CaseNote


class WorkSite(models.Model):
    """Pit Stop work sites where clients can be assigned"""
    
    SITE_TYPE_CHOICES = [
        ('pitstop', 'Pit Stop Location'),
        ('special_event', 'Special Event'),
        ('other', 'Other Site')
    ]
    
    name = models.CharField(max_length=200, help_text='Site name (e.g., "Mission & 16th Pit Stop")')
    site_type = models.CharField(max_length=20, choices=SITE_TYPE_CHOICES, default='pitstop')
    address = models.CharField(max_length=300)
    neighborhood = models.CharField(max_length=100, blank=True)
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text='GPS latitude for clock-in/out geofence validation.',
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text='GPS longitude for clock-in/out geofence validation.',
    )
    
    # Site details
    supervisor_name = models.CharField(max_length=100, blank=True)
    supervisor_phone = models.CharField(max_length=20, blank=True)
    supervisor_email = models.EmailField(blank=True)
    
    # Shift information
    typical_start_time = models.TimeField(help_text='Typical shift start time')
    typical_end_time = models.TimeField(blank=True, null=True, help_text='Typical shift end time (optional)')
    available_time_slots = models.JSONField(
        default=list,
        help_text='Available time slots: ["6-12", "13-21", "22-5"]'
    )
    max_workers_per_shift = models.IntegerField(default=2, help_text='Maximum workers per shift')
    
    # Status
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Work Site'
        verbose_name_plural = 'Work Sites'
    
    def __str__(self):
        return f"{self.name} ({self.neighborhood})" if self.neighborhood else self.name
    
    @property
    def current_assignments_count(self):
        """Count of current active assignments"""
        from datetime import date
        return self.assignments.filter(
            assignment_date=date.today(),
            status__in=['confirmed', 'in_progress']
        ).count()
    
    @property
    def has_capacity_today(self):
        """Check if site has capacity for more workers today"""
        return self.current_assignments_count < self.max_workers_per_shift


class WorkAssignment(models.Model):
    """Track work assignments for clients at Pit Stop sites"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending Confirmation'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('no_show', 'No Show'),
        ('called_out', 'Called Out'),
        ('cancelled', 'Cancelled')
    ]
    
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='work_assignments')
    work_site = models.ForeignKey(WorkSite, on_delete=models.CASCADE, related_name='assignments')
    
    # Assignment details
    assignment_date = models.DateField(help_text='Date of work assignment')
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    confirmed_by_client = models.BooleanField(default=False)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    
    # Assignment management
    assigned_by = models.CharField(max_length=100, help_text='Staff member who made the assignment')
    assignment_notes = models.TextField(blank=True)
    
    # Call-out tracking
    called_out_at = models.DateTimeField(null=True, blank=True)
    callout_reason = models.TextField(blank=True)
    replacement_found = models.BooleanField(default=False)
    replacement_client = models.ForeignKey(
        Client, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='replacement_assignments'
    )
    
    # Completion tracking
    hours_worked = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    performance_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-assignment_date', 'start_time']
        verbose_name = 'Work Assignment'
        verbose_name_plural = 'Work Assignments'
    
    def __str__(self):
        return f"{self.client.full_name} → {self.work_site.name} on {self.assignment_date}"
    
    def clean(self):
        """Validate assignment doesn't exceed site capacity"""
        if self.pk:
            return
        
        same_day_assignments = WorkAssignment.objects.filter(
            work_site=self.work_site,
            assignment_date=self.assignment_date,
            status__in=['confirmed', 'pending', 'in_progress']
        ).count()
        
        if same_day_assignments >= self.work_site.max_workers_per_shift:
            raise ValidationError(
                f"{self.work_site.name} is already at capacity ({self.work_site.max_workers_per_shift} workers) for {self.assignment_date}"
            )
    
    @property
    def is_today(self):
        from datetime import date
        return self.assignment_date == date.today()
    
    @property
    def is_upcoming(self):
        from datetime import date
        return self.assignment_date > date.today()
    
    @property
    def needs_replacement(self):
        """Check if this assignment was called out and needs a replacement"""
        return self.status == 'called_out' and not self.replacement_found


class WorkerTimePunch(models.Model):
    """
    Worker clock in/out records with optional geolocation verification.
    """

    GEO_STATUS_CAPTURED = 'captured'
    GEO_STATUS_DENIED = 'denied'
    GEO_STATUS_UNAVAILABLE = 'unavailable'
    GEO_STATUS_TIMEOUT = 'timeout'
    GEO_STATUS_ERROR = 'error'
    GEO_STATUS_SKIPPED = 'skipped'

    GEO_STATUS_CHOICES = [
        (GEO_STATUS_CAPTURED, 'Location captured'),
        (GEO_STATUS_DENIED, 'Location permission denied'),
        (GEO_STATUS_UNAVAILABLE, 'Location unavailable'),
        (GEO_STATUS_TIMEOUT, 'Location lookup timed out'),
        (GEO_STATUS_ERROR, 'Location lookup failed'),
        (GEO_STATUS_SKIPPED, 'Location not attempted'),
    ]

    worker_account = models.ForeignKey(
        'WorkerAccount',
        on_delete=models.CASCADE,
        related_name='time_punches',
    )
    assignment = models.ForeignKey(
        WorkAssignment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='time_punches',
        help_text='Work assignment this punch belongs to. New punches should always set this.',
    )
    work_site = models.ForeignKey(
        WorkSite,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='time_punches',
        help_text='PitStop location selected for this clock in/out.',
    )
    clock_in_at = models.DateTimeField()
    clock_out_at = models.DateTimeField(null=True, blank=True)

    # Server-anchored times (authoritative for verification/audits).
    clock_in_server_received_at = models.DateTimeField(auto_now_add=True)
    clock_out_server_received_at = models.DateTimeField(null=True, blank=True)
    clock_in_client_reported_at = models.DateTimeField(null=True, blank=True)
    clock_out_client_reported_at = models.DateTimeField(null=True, blank=True)

    clock_in_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    clock_in_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    clock_in_accuracy_meters = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    clock_in_geo_status = models.CharField(
        max_length=20,
        choices=GEO_STATUS_CHOICES,
        default=GEO_STATUS_SKIPPED,
    )
    clock_in_geo_error = models.CharField(max_length=200, blank=True)
    clock_in_geo_basic_ok = models.BooleanField(
        default=False,
        help_text='Basic validation check for clock-in location payload.',
    )
    clock_in_geo_basic_note = models.CharField(max_length=200, blank=True)

    clock_out_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    clock_out_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    clock_out_accuracy_meters = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    clock_out_geo_status = models.CharField(
        max_length=20,
        choices=GEO_STATUS_CHOICES,
        default=GEO_STATUS_SKIPPED,
    )
    clock_out_geo_error = models.CharField(max_length=200, blank=True)
    clock_out_geo_basic_ok = models.BooleanField(
        default=False,
        help_text='Basic validation check for clock-out location payload.',
    )
    clock_out_geo_basic_note = models.CharField(max_length=200, blank=True)

    # Unpaid meal break (single lunch per shift). Paid 10-minute rest breaks are
    # not tracked because they do not affect net paid hours. lat/long captured
    # for audit, mirroring the clock-in/out geolocation.
    lunch_start_at = models.DateTimeField(null=True, blank=True)
    lunch_end_at = models.DateTimeField(null=True, blank=True)
    lunch_start_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    lunch_start_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    lunch_end_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    lunch_end_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    class Meta:
        ordering = ['-clock_in_at']
        verbose_name = 'Worker Time Punch'
        verbose_name_plural = 'Worker Time Punches'
        indexes = [
            models.Index(fields=['worker_account', 'clock_out_at']),
            models.Index(fields=['assignment', 'clock_out_at']),
            models.Index(fields=['work_site', 'clock_out_at']),
            models.Index(fields=['clock_in_at']),
        ]

    def __str__(self):
        return f"{self.worker_account.client.full_name} clock-in {self.clock_in_at}"

    @property
    def is_on_lunch(self):
        return self.lunch_start_at is not None and self.lunch_end_at is None

    @property
    def lunch_minutes(self):
        """Completed lunch length in minutes, or 0 if no completed lunch."""
        if not self.lunch_start_at or not self.lunch_end_at:
            return 0
        seconds = max((self.lunch_end_at - self.lunch_start_at).total_seconds(), 0)
        return int(seconds // 60)

    @property
    def net_hours(self):
        """Paid hours = worked time minus the unpaid lunch. None if still open."""
        if not self.clock_in_at or not self.clock_out_at:
            return None
        worked = max((self.clock_out_at - self.clock_in_at).total_seconds(), 0)
        net_seconds = max(worked - self.lunch_minutes * 60, 0)
        return round(net_seconds / 3600, 2)


class ClientTextMessage(models.Model):
    """SMS log for client/worker outreach sent through Azure Communication Services."""

    DIRECTION_OUTBOUND = 'outbound'
    DIRECTION_INBOUND = 'inbound'

    STATUS_PENDING = 'pending'
    STATUS_SENT = 'sent'
    STATUS_FAILED = 'failed'
    STATUS_RECEIVED = 'received'

    PURPOSE_PROGRESS_FOLLOWUP = 'progress_followup'
    PURPOSE_ASSIGNMENT = 'assignment'
    PURPOSE_GENERAL = 'general'

    DIRECTION_CHOICES = [
        (DIRECTION_OUTBOUND, 'Outbound'),
        (DIRECTION_INBOUND, 'Inbound'),
    ]
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_SENT, 'Sent'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_RECEIVED, 'Received'),
    ]
    PURPOSE_CHOICES = [
        (PURPOSE_PROGRESS_FOLLOWUP, 'Progress follow-up'),
        (PURPOSE_ASSIGNMENT, 'Assignment'),
        (PURPOSE_GENERAL, 'General'),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='text_messages')
    direction = models.CharField(max_length=20, choices=DIRECTION_CHOICES, default=DIRECTION_OUTBOUND)
    purpose = models.CharField(max_length=30, choices=PURPOSE_CHOICES, default=PURPOSE_GENERAL)
    checkpoint_days = models.PositiveIntegerField(null=True, blank=True)
    dedupe_key = models.CharField(max_length=120, unique=True, null=True, blank=True)
    to_phone = models.CharField(max_length=20, blank=True)
    from_phone = models.CharField(max_length=20, blank=True)
    body = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    provider_message_id = models.CharField(max_length=120, blank=True)
    provider_response = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Client Text Message'
        verbose_name_plural = 'Client Text Messages'
        indexes = [
            models.Index(fields=['client', 'purpose', 'checkpoint_days']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['direction', 'created_at']),
        ]

    def __str__(self):
        return f"{self.client.full_name} {self.purpose} SMS {self.status}"


class WorkerAccount(models.Model):
    """Authentication account for PitStop workers to access worker portal"""

    STATUS_APPLICANT = 'applicant'
    STATUS_ACTIVE = 'active'
    STATUS_INACTIVE = 'inactive'

    STATUS_CHOICES = [
        (STATUS_APPLICANT, 'Applicant'),
        (STATUS_ACTIVE, 'Active Worker'),
        (STATUS_INACTIVE, 'Inactive'),
    ]
    
    client = models.OneToOneField(
        Client, 
        on_delete=models.CASCADE, 
        related_name='worker_account',
        help_text='Link to client record'
    )
    phone = models.CharField(
        max_length=20, 
        unique=True,
        help_text='Phone number for login (must match client phone)'
    )
    pin_hash = models.CharField(
        max_length=128,
        help_text='Hashed 4-6 digit PIN for authentication'
    )
    
    # Account status (single gate: is_active = can use portal; is_approved is kept in sync for legacy/admin)
    is_active = models.BooleanField(
        default=True,
        verbose_name='Portal access',
        help_text='When on, this worker can log in to the PitStop worker portal.',
    )
    is_approved = models.BooleanField(
        default=True,
        help_text='Synced with portal access; kept for compatibility'
    )
    worker_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_APPLICANT,
        help_text='Roster status: applicant, active worker, or inactive.',
    )
    is_available = models.BooleanField(
        default=True,
        help_text='Simple roster availability toggle. Replaces time-slot availability.',
    )
    
    # Login tracking
    last_login = models.DateTimeField(null=True, blank=True)
    login_attempts = models.IntegerField(default=0)
    locked_until = models.DateTimeField(
        null=True, 
        blank=True,
        help_text='Account locked until this time after too many failed attempts'
    )
    
    # Account management
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=100, blank=True, help_text='Staff member who created account')
    notes = models.TextField(blank=True)
    follow_up_notes = models.TextField(
        blank=True,
        help_text='Roster notes / follow-up history visible to staff.',
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Worker Account'
        verbose_name_plural = 'Worker Accounts'
    
    def __str__(self):
        return f"{self.client.full_name} - {self.phone}"

    def save(self, *args, **kwargs):
        """One flag for portal access; store phone as digits so login matches mobile keyboards."""
        from .phone_utils import normalize_login_phone

        self.is_approved = self.is_active
        if self.phone:
            d = normalize_login_phone(self.phone)
            if d:
                self.phone = d
        super().save(*args, **kwargs)

    def check_pin(self, raw_pin):
        """Check if provided PIN matches stored hash"""
        from django.contrib.auth.hashers import check_password
        return check_password(raw_pin, self.pin_hash)
    
    def set_pin(self, raw_pin):
        """Set PIN with hashing"""
        from django.contrib.auth.hashers import make_password
        self.pin_hash = make_password(raw_pin)
    
    @property
    def is_locked(self):
        """Check if account is currently locked"""
        if not self.locked_until:
            return False
        from django.utils import timezone
        return timezone.now() < self.locked_until
    
    def increment_login_attempts(self):
        """Increment failed login attempts and lock if necessary"""
        self.login_attempts += 1
        if self.login_attempts >= 5:
            from django.utils import timezone
            from datetime import timedelta
            self.locked_until = timezone.now() + timedelta(minutes=30)
        self.save()
    
    def reset_login_attempts(self):
        """Reset login attempts on successful login"""
        self.login_attempts = 0
        self.locked_until = None
        from django.utils import timezone
        self.last_login = timezone.now()
        self.save()


class WorkerSessionToken(models.Model):
    """
    Persistent worker portal session token.

    IMPORTANT: Previously sessions were stored in memory (per-process). On Azure/Gunicorn,
    this causes "login loops" because the next request may hit a different worker process
    that doesn't have the in-memory session. Storing tokens in the DB makes sessions stable.
    """
    token = models.CharField(max_length=64, unique=True)
    worker_account = models.ForeignKey(
        WorkerAccount,
        on_delete=models.CASCADE,
        related_name='sessions',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"WorkerSessionToken({self.worker_account.phone})"

