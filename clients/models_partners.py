"""
Partner referral ingest (write-only mail slot).

Partners authenticate with a hashed API key. They can POST referrals; they cannot
list or read client records through this surface.
"""
from __future__ import annotations

import hashlib
import secrets

from django.db import models
from django.utils import timezone

from .models import Client


def hash_partner_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode('utf-8')).hexdigest()


def generate_partner_api_key() -> str:
    """Return a URL-safe key. Show once; only the hash is stored."""
    return f'mhh_pk_{secrets.token_urlsafe(32)}'


class Partner(models.Model):
    """External organization allowed to push referrals into MHH."""

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=80, unique=True)
    contact_name = models.CharField(max_length=120, blank=True)
    contact_email = models.EmailField(blank=True)
    is_active = models.BooleanField(
        default=True,
        help_text='Off = all API calls with this partner’s key are rejected.',
    )
    notes = models.TextField(blank=True, help_text='Internal notes (contracts, billing).')

    # API key: store hash + short prefix for identification. Raw key shown once in admin.
    api_key_prefix = models.CharField(max_length=16, blank=True, editable=False)
    api_key_hash = models.CharField(max_length=64, blank=True, editable=False, db_index=True)
    api_key_created_at = models.DateTimeField(null=True, blank=True, editable=False)

    request_count = models.PositiveIntegerField(
        default=0,
        help_text='Successful ingest calls (for invoice support).',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Partner'
        verbose_name_plural = 'Partners'

    def __str__(self):
        return self.name

    def set_api_key(self, raw_key: str | None = None) -> str:
        """Hash and store a new API key. Returns the raw key (show once)."""
        raw = raw_key or generate_partner_api_key()
        self.api_key_hash = hash_partner_api_key(raw)
        self.api_key_prefix = raw[:12]
        self.api_key_created_at = timezone.now()
        return raw

    def check_api_key(self, raw_key: str) -> bool:
        if not self.is_active or not self.api_key_hash or not raw_key:
            return False
        return secrets.compare_digest(self.api_key_hash, hash_partner_api_key(raw_key))


class PartnerReferral(models.Model):
    """Inbound referral for staff review — does not auto-create a Client."""

    STATUS_PENDING = 'pending'
    STATUS_REVIEWED = 'reviewed'
    STATUS_ACCEPTED = 'accepted'
    STATUS_DECLINED = 'declined'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending review'),
        (STATUS_REVIEWED, 'Reviewed'),
        (STATUS_ACCEPTED, 'Accepted'),
        (STATUS_DECLINED, 'Declined'),
    ]

    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name='referrals')
    external_id = models.CharField(
        max_length=120,
        help_text='Partner’s stable id (e.g. Airtable record id).',
    )

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    notes = models.TextField(blank=True, max_length=2000)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    staff_notes = models.TextField(blank=True, help_text='Internal follow-up notes.')
    linked_client = models.ForeignKey(
        Client,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='partner_referrals',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Partner referral'
        verbose_name_plural = 'Partner referrals'
        constraints = [
            models.UniqueConstraint(
                fields=['partner', 'external_id'],
                name='uniq_partner_referral_external_id',
            ),
        ]
        indexes = [
            models.Index(fields=['partner', 'status']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f'{self.first_name} {self.last_name} ({self.partner.slug})'


class PartnerApiAuditLog(models.Model):
    """Lightweight audit of partner API calls (no full PII payload retained)."""

    partner = models.ForeignKey(
        Partner,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='audit_logs',
    )
    method = models.CharField(max_length=10)
    path = models.CharField(max_length=200)
    status_code = models.PositiveSmallIntegerField()
    external_id = models.CharField(max_length=120, blank=True)
    detail = models.CharField(max_length=200, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Partner API audit log'
        verbose_name_plural = 'Partner API audit logs'
        indexes = [
            models.Index(fields=['partner', '-created_at']),
        ]

    def __str__(self):
        who = self.partner.slug if self.partner_id else 'unknown'
        return f'{who} {self.method} {self.status_code} @ {self.created_at:%Y-%m-%d %H:%M}'
