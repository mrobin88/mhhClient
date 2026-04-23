"""
Phone helpers for worker portal login and account setup.

Stored numbers may include formatting; workers typically enter digits only.
"""
import re

from django.db import connection
from django.db.models import Q


def phone_digits(phone) -> str:
    if phone is None:
        return ''
    return re.sub(r'\D', '', str(phone))


def normalize_login_phone(phone) -> str:
    """
    Normalize worker login phone to a predictable digits-only format.
    - Strips common extension markers (ext, x, # and trailing digits)
    - Converts +1XXXXXXXXXX / 1XXXXXXXXXX to 10-digit US format
    """
    if phone is None:
        return ''
    raw = str(phone).strip()
    # Remove extension chunks before digit extraction.
    raw = re.split(r'(?i)\b(?:ext\.?|x|#)\b', raw)[0]
    d = phone_digits(raw)
    if len(d) == 11 and d.startswith('1'):
        d = d[1:]
    return d


def default_worker_pin_from_phone(phone) -> str:
    """Last four digits of the phone number (not the last four characters)."""
    d = normalize_login_phone(phone)
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
    digits = normalize_login_phone(phone_raw)
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
        if normalize_login_phone(obj.phone) == digits:
            return obj
    return None


def find_all_by_normalized_phone(queryset, phone_raw: str):
    """
    All rows whose phone matches phone_raw when compared as digits-only
    (same rules as find_by_normalized_phone, but returns every match).
    """
    digits = normalize_login_phone(phone_raw)
    if not digits:
        return queryset.none()

    q = Q()
    if phone_raw:
        q |= Q(phone=phone_raw)
    q |= Q(phone=digits)
    exact = queryset.filter(q).distinct()
    if exact.exists():
        return exact

    model = queryset.model
    table = model._meta.db_table

    if connection.vendor == 'postgresql':
        return queryset.extra(
            where=[f"regexp_replace({table}.phone, '[^0-9]', '', 'g') = %s"],
            params=[digits],
        ).distinct()

    pks = []
    for obj in queryset.iterator(chunk_size=500):
        if normalize_login_phone(obj.phone) == digits:
            pks.append(obj.pk)
    if not pks:
        return queryset.none()
    return queryset.filter(pk__in=pks).distinct()
