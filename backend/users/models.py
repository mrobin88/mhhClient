from django.contrib.auth.models import AbstractUser
from django.db import models

class StaffUser(AbstractUser):
    """Custom user model for staff members"""
    STAFF_ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('case_manager', 'Case Manager'),
        ('counselor', 'Counselor'),
        ('volunteer', 'Volunteer'),
    ]
    
    role = models.CharField(max_length=20, choices=STAFF_ROLE_CHOICES, default='case_manager')
    phone = models.CharField(max_length=15, blank=True, null=True)
    nonprofit = models.CharField(max_length=100, blank=True, null=True)
    
    # Override inherited fields to ensure proper defaults
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(
        default=False,
        help_text='Designates whether the user can log into the admin site.'
    )
    
    class Meta:
        verbose_name = 'Staff User'
        verbose_name_plural = 'Staff Users'
        db_table = 'users_staffuser'  # Explicit table name
    
    def __str__(self):
        if self.get_full_name():
            return f"{self.get_full_name()} ({self.get_role_display()})"
        return f"{self.username} ({self.get_role_display()})"
    
    def save(self, *args, **kwargs):
        # Ensure staff users have is_staff=True by default for admin access
        if self.role in ['admin', 'case_manager', 'counselor'] and not self.is_staff:
            self.is_staff = True
        super().save(*args, **kwargs)
