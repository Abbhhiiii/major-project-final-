from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4


@dataclass(frozen=True)
class Organization:
    name: str
    emergency_contact: str = ""
    notification_preference: str = "dashboard"
    api_key_last_four: str = ""
    api_key_fingerprint: str = ""
    organization_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(frozen=True)
class UserAccount:
    organization_id: str
    email: str
    password_hash: str
    user_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(frozen=True)
class CameraRegistration:
    organization_id: str
    name: str
    location: str
    camera_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(frozen=True)
class KnowledgeDocument:
    organization_id: str
    filename: str
    stored_name: str
    page_count: int
    chunk_count: int
    document_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
