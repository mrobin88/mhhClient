"""
Class/training scheduling: recurring templates, generated dated sessions, and roster enrollments.

Mirrors the "recurring meeting" mental model (does not repeat / weekly on X / monthly on
the Nth X of every month) so staff can set a class up once and have upcoming sessions
generated automatically, instead of hand-adding dates every time.
"""
from calendar import monthrange
from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from .models import Client


class ClassTemplate(models.Model):
    """A class/training offering — one-time or recurring (weekly or monthly)."""

    CATEGORY_CHOICES = [
        ('orientation', 'Orientation'),
        ('job_readiness', 'Job Readiness Training'),
        ('resume_workshop', 'Resume & Application Workshop'),
        ('training', 'Skills Training'),
        ('other', 'Other'),
    ]

    RECURRENCE_CHOICES = [
        ('none', 'Does not repeat'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]

    WEEKDAY_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]

    WEEK_OF_MONTH_CHOICES = [
        (1, '1st'),
        (2, '2nd'),
        (3, '3rd'),
        (4, '4th'),
    ]

    name = models.CharField(max_length=150, help_text='e.g. "New Client Orientation" or "Resume Workshop"')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='training')
    description = models.TextField(blank=True)
    location = models.CharField(max_length=200, blank=True, help_text='Room or address; can be overridden per session.')
    facilitator = models.CharField(max_length=100, blank=True, help_text='Staff member or presenter running this class.')
    capacity = models.PositiveIntegerField(default=20, help_text='Default seat limit for generated sessions.')

    start_time = models.TimeField(help_text='Default start time for generated sessions.')
    end_time = models.TimeField(help_text='Default end time for generated sessions.')

    recurrence = models.CharField(max_length=10, choices=RECURRENCE_CHOICES, default='none')
    recurrence_weekday = models.PositiveSmallIntegerField(
        choices=WEEKDAY_CHOICES,
        null=True,
        blank=True,
        help_text='Required for weekly/monthly recurrence.',
    )
    recurrence_week_of_month = models.PositiveSmallIntegerField(
        choices=WEEK_OF_MONTH_CHOICES,
        null=True,
        blank=True,
        help_text='Required for monthly recurrence, e.g. 2nd Tuesday of every month.',
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Class / Training Template'
        verbose_name_plural = 'Classes & Trainings'

    def __str__(self):
        return self.name

    def clean(self):
        errors = {}
        if self.recurrence in ('weekly', 'monthly') and self.recurrence_weekday is None:
            errors['recurrence_weekday'] = 'Required for weekly or monthly recurrence.'
        if self.recurrence == 'monthly' and self.recurrence_week_of_month is None:
            errors['recurrence_week_of_month'] = 'Required for monthly recurrence.'
        if errors:
            raise ValidationError(errors)

    @property
    def recurrence_summary(self):
        if self.recurrence == 'none':
            return 'One-time'
        weekday_label = dict(self.WEEKDAY_CHOICES).get(self.recurrence_weekday, '')
        if self.recurrence == 'weekly':
            return f'Weekly on {weekday_label}'
        ordinal = dict(self.WEEK_OF_MONTH_CHOICES).get(self.recurrence_week_of_month, '')
        return f'Monthly — {ordinal} {weekday_label}'

    def _nth_weekday_of_month(self, year, month):
        first_day = date(year, month, 1)
        offset = (self.recurrence_weekday - first_day.weekday()) % 7
        day_number = 1 + offset + (self.recurrence_week_of_month - 1) * 7
        last_day_of_month = monthrange(year, month)[1]
        if day_number > last_day_of_month:
            return None
        return date(year, month, day_number)

    def upcoming_dates(self, horizon_days=60, today=None):
        """Compute session dates from today through horizon_days, per the recurrence rule."""
        today = today or timezone.localdate()
        end = today + timedelta(days=horizon_days)
        dates = []

        if self.recurrence == 'weekly' and self.recurrence_weekday is not None:
            offset = (self.recurrence_weekday - today.weekday()) % 7
            cursor = today + timedelta(days=offset)
            while cursor <= end:
                dates.append(cursor)
                cursor += timedelta(days=7)

        elif (
            self.recurrence == 'monthly'
            and self.recurrence_weekday is not None
            and self.recurrence_week_of_month
        ):
            cursor_year, cursor_month = today.year, today.month
            while date(cursor_year, cursor_month, 1) <= end:
                candidate = self._nth_weekday_of_month(cursor_year, cursor_month)
                if candidate and today <= candidate <= end:
                    dates.append(candidate)
                if cursor_month == 12:
                    cursor_year, cursor_month = cursor_year + 1, 1
                else:
                    cursor_month += 1

        return dates

    def generate_upcoming_sessions(self, horizon_days=60):
        """Create ClassSession rows for computed upcoming dates that don't already exist."""
        if self.recurrence == 'none' or not self.is_active:
            return []
        dates = self.upcoming_dates(horizon_days=horizon_days)
        if not dates:
            return []
        existing = set(
            self.sessions.filter(session_date__in=dates).values_list('session_date', flat=True)
        )
        created = []
        for session_date in dates:
            if session_date in existing:
                continue
            created.append(
                ClassSession.objects.create(
                    template=self,
                    session_date=session_date,
                    start_time=self.start_time,
                    end_time=self.end_time,
                    location=self.location,
                    facilitator=self.facilitator,
                    capacity=self.capacity,
                )
            )
        return created


class ClassSession(models.Model):
    """A specific date/time occurrence of a ClassTemplate, with its own roster."""

    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    template = models.ForeignKey(ClassTemplate, on_delete=models.CASCADE, related_name='sessions')
    session_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    location = models.CharField(max_length=200, blank=True)
    facilitator = models.CharField(max_length=100, blank=True)
    capacity = models.PositiveIntegerField(default=20)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='scheduled')
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['session_date', 'start_time']
        verbose_name = 'Class Session'
        verbose_name_plural = 'Class Sessions'
        indexes = [
            models.Index(fields=['session_date'], name='classsession_date_idx'),
            models.Index(fields=['status', 'session_date'], name='classsession_status_date_idx'),
        ]

    def __str__(self):
        return f'{self.template.name} — {self.session_date.isoformat()}'

    @property
    def enrolled_count(self):
        return self.enrollments.filter(status__in=['registered', 'attended']).count()

    @property
    def spots_remaining(self):
        return max(self.capacity - self.enrolled_count, 0)


class ClassEnrollment(models.Model):
    """Roster entry: one client's registration/attendance for a specific class session."""

    STATUS_CHOICES = [
        ('registered', 'Registered'),
        ('attended', 'Attended'),
        ('no_show', 'No Show'),
        ('cancelled', 'Cancelled'),
    ]

    session = models.ForeignKey(ClassSession, on_delete=models.CASCADE, related_name='enrollments')
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='class_enrollments')
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='registered')
    registered_by = models.CharField(max_length=100, blank=True, help_text='Staff member who added this client.')
    registered_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-registered_at']
        verbose_name = 'Class Roster Entry'
        verbose_name_plural = 'Class Roster'
        constraints = [
            models.UniqueConstraint(fields=['session', 'client'], name='uniq_class_session_client'),
        ]

    def __str__(self):
        return f'{self.client.full_name} — {self.session}'
