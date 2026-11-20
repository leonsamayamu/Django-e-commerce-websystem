"""Gateway credentials are encrypted at rest (Fernet). Key: FIELD_ENCRYPTION_KEY env var, else derived from SECRET_KEY.
If the key changes, stored credentials cannot be read and must be entered again."""
import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


def _fernet():
    key = os.environ.get("FIELD_ENCRYPTION_KEY")
    if not key:
        key = base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode()).digest())
    return Fernet(key)


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode() if value else ""


def decrypt(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode()).decode() if token else ""
    except InvalidToken:
        return ""
