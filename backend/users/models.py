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
    phone = models.CharField(max_length=15, blank=True)
    nonprofit = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Staff User'
        verbose_name_plural = 'Staff Users'
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.role})"
