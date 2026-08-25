"""Application-level encrypted model fields for sensitive client data."""

import logging

from django.conf import settings
from django.db import models


ENCRYPTED_PREFIX = "enc:"
logger = logging.getLogger("clients")
_logged_unusable_keyring = False


def _configured_fernet_keys():
    """Return configured Fernet instances keyed by rotation id.

    Never raise: a bad Azure app setting must not take down signup, staff
    save, or document upload. Invalid keyrings are treated as unconfigured.
    """
    from cryptography.fernet import Fernet

    configured = getattr(settings, "SSN_ENCRYPTION_KEYS", {}) or {}
    if not isinstance(configured, dict) or not configured:
        return {}
    try:
        return {str(key_id): Fernet(value.encode("ascii")) for key_id, value in configured.items()}
    except Exception:
        global _logged_unusable_keyring
        if not _logged_unusable_keyring:
            logger.exception("SSN_ENCRYPTION_KEYS is not a usable Fernet keyring; storing SSN as-is.")
            _logged_unusable_keyring = True
        return {}


def ssn_encryption_is_configured():
    keys = _configured_fernet_keys()
    active_key_id = str(getattr(settings, "SSN_ACTIVE_KEY_ID", "v1"))
    return active_key_id in keys


def encrypt_sensitive_value(value):
    if value in (None, ""):
        return value
    if isinstance(value, str) and value.startswith(ENCRYPTED_PREFIX):
        return value
    if not ssn_encryption_is_configured():
        # Production currently has no keyring. Do not fail staff/public saves;
        # keep the existing value until keys are configured.
        return value

    try:
        keys = _configured_fernet_keys()
        active_key_id = str(getattr(settings, "SSN_ACTIVE_KEY_ID", "v1"))
        token = keys[active_key_id].encrypt(str(value).encode("utf-8")).decode("ascii")
        return f"{ENCRYPTED_PREFIX}{active_key_id}:{token}"
    except Exception:
        logger.exception("SSN encryption failed; persisting the value without encryption.")
        return value


def decrypt_sensitive_value(value):
    if value in (None, "") or not isinstance(value, str):
        return value
    if not value.startswith(ENCRYPTED_PREFIX):
        # Legacy rows remain readable until the encryption backfill is run.
        return value

    from cryptography.fernet import InvalidToken

    try:
        _, key_id, token = value.split(":", 2)
    except ValueError:
        return value

    key = _configured_fernet_keys().get(key_id)
    if key is None:
        return value
    try:
        return key.decrypt(token.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError, TypeError):
        return value


class EncryptedSSNField(models.TextField):
    """Transparently encrypt SSNs before database persistence."""

    description = "SSN encrypted with the configured application key"

    def from_db_value(self, value, expression, connection):
        try:
            return decrypt_sensitive_value(value)
        except Exception:
            logger.exception("SSN decrypt failed while loading a client row.")
            return value

    def to_python(self, value):
        try:
            return decrypt_sensitive_value(value)
        except Exception:
            return value

    def get_prep_value(self, value):
        prepared = super().get_prep_value(value)
        try:
            return encrypt_sensitive_value(prepared)
        except Exception:
            logger.exception("SSN encrypt failed while preparing a client row.")
            return prepared
