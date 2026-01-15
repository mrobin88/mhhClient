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
    
    # Site details
    supervisor_name = models.CharField(max_length=100, blank=True)
    supervisor_phone = models.CharField(max_length=20, blank=True)
    supervisor_email = models.EmailField(blank=True)
    
    # Shift information
    typical_start_time = models.TimeField(help_text='Typical shift start time')
    typical_end_time = models.TimeField(help_text='Typical shift end time')
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


class ClientAvailability(models.Model):
    """Track client availability for work assignments"""
    
    DAY_CHOICES = [
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday')
    ]
    
    TIME_SLOT_CHOICES = [
        ('6-12', '6am-12pm'),
        ('13-21', '1pm-9pm'),
        ('22-5', '10pm-5am'),
    ]
    
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='availability')
    
    # Regular weekly availability
    day_of_week = models.CharField(max_length=10, choices=DAY_CHOICES)
    available = models.BooleanField(default=True)
    preferred_time_slots = models.JSONField(
        default=list,
        help_text='List of preferred time slots: ["6-12", "13-21", "22-5"]'
    )
    
    # Legacy time fields (for backward compatibility)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    
    # Notes
    notes = models.TextField(blank=True, help_text='e.g., "Can only work mornings", "Available after 2pm"')
    
    class Meta:
        ordering = ['client', 'day_of_week']
        verbose_name = 'Client Availability'
        verbose_name_plural = 'Client Availabilities'
        unique_together = ['client', 'day_of_week']
    
    def __str__(self):
        status = "Available" if self.available else "Not available"
        return f"{self.client.full_name} - {self.get_day_of_week_display()}: {status}"


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
        if self.pk:  # Only check for existing assignments
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


class CallOutLog(models.Model):
    """Detailed log of call-outs for reporting and tracking"""
    
    assignment = models.OneToOneField(WorkAssignment, on_delete=models.CASCADE, related_name='callout_log')
    
    # Call-out details
    reported_at = models.DateTimeField(auto_now_add=True)
    reported_by = models.CharField(max_length=100, help_text='Who received the call-out')
    reason = models.TextField(help_text='Reason for call-out')
    advance_notice_hours = models.IntegerField(help_text='How many hours notice was given')
    
    # Actions taken
    replacement_contacted_count = models.IntegerField(default=0, help_text='Number of replacements contacted')
    replacement_found_at = models.DateTimeField(null=True, blank=True)
    
    # Follow-up
    client_contacted_after = models.BooleanField(default=False)
    follow_up_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-reported_at']
        verbose_name = 'Call-Out Log'
        verbose_name_plural = 'Call-Out Logs'
    
    def __str__(self):
        return f"Call-out: {self.assignment.client.full_name} - {self.assignment.assignment_date}"
    
    @property
    def is_last_minute(self):
        """Check if call-out was less than 4 hours notice"""
        return self.advance_notice_hours < 4


class WorkerAccount(models.Model):
    """Authentication account for PitStop workers to access worker portal"""
    
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
    
    # Account status
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this worker can access the portal'
    )
    is_approved = models.BooleanField(
        default=False,
        help_text='Whether account is approved by staff'
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
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Worker Account'
        verbose_name_plural = 'Worker Accounts'
    
    def __str__(self):
        return f"{self.client.full_name} - {self.phone}"
    
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


class ServiceRequest(models.Model):
    """Worker-submitted issues and service requests at work sites"""
    
    ISSUE_TYPE_CHOICES = [
        ('bathroom', 'Bathroom Issue'),
        ('supplies', 'Supplies Needed'),
        ('safety', 'Safety Concern'),
        ('equipment', 'Equipment Problem'),
        ('cleaning', 'Cleaning Issue'),
        ('other', 'Other')
    ]
    
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('acknowledged', 'Acknowledged'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed')
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent')
    ]
    
    # Who and where
    submitted_by = models.ForeignKey(
        Client, 
        on_delete=models.CASCADE,
        related_name='service_requests',
        help_text='Worker who submitted this request'
    )
    work_site = models.ForeignKey(
        WorkSite,
        on_delete=models.CASCADE,
        related_name='service_requests',
        help_text='Site where issue is located'
    )
    
    # Issue details
    issue_type = models.CharField(max_length=20, choices=ISSUE_TYPE_CHOICES)
    title = models.CharField(max_length=200, help_text='Brief description of issue')
    description = models.TextField(help_text='Detailed description of the problem')
    location_detail = models.CharField(
        max_length=200,
        blank=True,
        help_text='Specific location at site (e.g., "North bathroom", "Storage closet")'
    )
    
    # Prioritization and status
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    
    # Evidence
    photo = models.ImageField(
        upload_to='service_requests/',
        blank=True,
        null=True,
        help_text='Photo of the issue'
    )
    
    # Response tracking
    acknowledged_by = models.CharField(max_length=100, blank=True, help_text='Staff member who acknowledged')
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    assigned_to = models.CharField(max_length=100, blank=True, help_text='Person assigned to fix')
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Service Request'
        verbose_name_plural = 'Service Requests'
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['work_site', 'status']),
        ]
    
    def __str__(self):
        return f"{self.get_issue_type_display()} at {self.work_site.name} - {self.title}"
    
    @property
    def is_overdue(self):
        """Check if request is overdue based on priority"""
        from django.utils import timezone
        from datetime import timedelta
        
        if self.status in ['resolved', 'closed']:
            return False
        
        age = timezone.now() - self.created_at
        
        if self.priority == 'urgent' and age > timedelta(hours=2):
            return True
        elif self.priority == 'high' and age > timedelta(hours=24):
            return True
        elif self.priority == 'medium' and age > timedelta(days=3):
            return True
        elif self.priority == 'low' and age > timedelta(days=7):
            return True
        
        return False
    
    @property
    def response_time(self):
        """Calculate time to acknowledgement"""
        if self.acknowledged_at:
            return self.acknowledged_at - self.created_at
        return None
    
    @property
    def resolution_time(self):
        """Calculate time to resolution"""
        if self.resolved_at:
            return self.resolved_at - self.created_at
        return None

