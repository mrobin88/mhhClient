"""
Staff attribution helpers for client records (case manager / staff_name).
"""


def staff_display_name(user):
    return (user.get_full_name() or '').strip() or user.username


def staff_skips_client_auto_assign(user):
    """
    Admin-level staff do not auto-assign clients when they touch a record.
    """
    if not user or not getattr(user, 'is_authenticated', False):
        return True
    if getattr(user, 'is_superuser', False):
        return True
    return getattr(user, 'role', None) == 'admin'


def apply_staff_assignment_to_client(client, user):
    """
    Assign client to the staff member processing this save/update.
    Returns True when staff_name was set/changed.
    """
    if staff_skips_client_auto_assign(user):
        return False
    client.staff_name = staff_display_name(user)
    return True
