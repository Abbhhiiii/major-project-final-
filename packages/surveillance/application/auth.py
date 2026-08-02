import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime


def hash_password(password: str, salt: bytes | None = None) -> str:
    actual_salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), actual_salt, 210_000)
    return f"{actual_salt.hex()}:{digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    salt_hex, expected = encoded.split(":", 1)
    candidate = hash_password(password, bytes.fromhex(salt_hex)).split(":", 1)[1]
    return hmac.compare_digest(candidate, expected)


def fingerprint_api_key(api_key: str) -> tuple[str, str]:
    return hashlib.sha256(api_key.encode()).hexdigest(), api_key[-4:]


@dataclass(frozen=True)
class AuthSession:
    token: str
    user_id: str
    organization_id: str
    expires_at: datetime
