"""
Phone helpers for worker portal login and account setup.

Stored numbers may include formatting; workers typically enter digits only.
"""
import re

from django.db import connection


def phone_digits(phone) -> str:
    if phone is None:
        return ''
    return re.sub(r'\D', '', str(phone))


def default_worker_pin_from_phone(phone) -> str:
    """Last four digits of the phone number (not the last four characters)."""
    d = phone_digits(phone)
    if len(d) >= 4:
        return d[-4:]
    if d:
        return d.ljust(4, '0')[:4]
    return '1234'


def find_by_normalized_phone(queryset, phone_raw: str):
    """
    Find a model instance whose `phone` field matches the given input when
    both are reduced to digits-only (plus exact-match fallbacks).
    """
    digits = phone_digits(phone_raw)
    if not digits:
        return None

    for candidate in (phone_raw, digits):
        if candidate:
            hit = queryset.filter(phone=candidate).first()
            if hit:
                return hit

    model = queryset.model
    table = model._meta.db_table

    if connection.vendor == 'postgresql':
        hit = queryset.extra(
            where=[f"regexp_replace({table}.phone, '[^0-9]', '', 'g') = %s"],
            params=[digits],
        ).first()
        if hit:
            return hit

    for obj in queryset.iterator(chunk_size=500):
        if phone_digits(obj.phone) == digits:
            return obj
    return None
