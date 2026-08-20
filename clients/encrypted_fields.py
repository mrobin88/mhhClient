"""Application-level encrypted model fields for sensitive client data."""

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models


ENCRYPTED_PREFIX = "enc:"


def _configured_fernet_keys():
    """Return configured Fernet instances keyed by rotation id."""
    from cryptography.fernet import Fernet

    configured = getattr(settings, "SSN_ENCRYPTION_KEYS", {})
    if not configured:
        return {}
    try:
        return {str(key_id): Fernet(value.encode("ascii")) for key_id, value in configured.items()}
    except (AttributeError, TypeError, ValueError) as exc:
        raise ImproperlyConfigured(
            "SSN_ENCRYPTION_KEYS must map key ids to valid Fernet keys."
        ) from exc


def encrypt_sensitive_value(value):
    if value in (None, ""):
        return value
    if isinstance(value, str) and value.startswith(ENCRYPTED_PREFIX):
        return value

    keys = _configured_fernet_keys()
    active_key_id = str(getattr(settings, "SSN_ACTIVE_KEY_ID", "v1"))
    if active_key_id not in keys:
        raise ImproperlyConfigured(
            f"SSN_ACTIVE_KEY_ID {active_key_id!r} is not configured in SSN_ENCRYPTION_KEYS."
        )
    token = keys[active_key_id].encrypt(str(value).encode("utf-8")).decode("ascii")
    return f"{ENCRYPTED_PREFIX}{active_key_id}:{token}"


def decrypt_sensitive_value(value):
    if value in (None, "") or not isinstance(value, str):
        return value
    if not value.startswith(ENCRYPTED_PREFIX):
        # Legacy rows remain readable until the encryption backfill is run.
        return value

    from cryptography.fernet import InvalidToken

    try:
        _, key_id, token = value.split(":", 2)
    except ValueError as exc:
        raise ValueError("Encrypted SSN has an invalid envelope.") from exc

    key = _configured_fernet_keys().get(key_id)
    if key is None:
        raise ImproperlyConfigured(f"Missing SSN encryption key {key_id!r}.")
    try:
        return key.decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Encrypted SSN could not be authenticated.") from exc


class EncryptedSSNField(models.TextField):
    """Transparently encrypt SSNs before database persistence."""

    description = "SSN encrypted with the configured application key"

    def from_db_value(self, value, expression, connection):
        return decrypt_sensitive_value(value)

    def to_python(self, value):
        return decrypt_sensitive_value(value)

    def get_prep_value(self, value):
        return encrypt_sensitive_value(super().get_prep_value(value))
