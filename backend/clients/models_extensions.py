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
    
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='availability')
    
    # Regular weekly availability
    day_of_week = models.CharField(max_length=10, choices=DAY_CHOICES)
    available = models.BooleanField(default=True)
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

