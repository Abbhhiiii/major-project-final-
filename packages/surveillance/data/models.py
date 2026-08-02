from datetime import datetime

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class IncidentRow(Base):
    __tablename__ = "incidents"

    incident_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    detection_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    rationale: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    alert_message: Mapped[str] = mapped_column(String(1000), nullable=False)
    organization_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    source_video_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    frame_timestamp_ms: Mapped[int | None] = mapped_column(nullable=True)
    stored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class AgentAuditRow(Base):
    __tablename__ = "agent_audits"

    audit_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    incident_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    detection_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    reasoning_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    reasoning_model: Mapped[str] = mapped_column(String(100), nullable=False)
    retrieval: Mapped[dict] = mapped_column(JSON, nullable=False)
    decision: Mapped[dict] = mapped_column(JSON, nullable=False)
    plan: Mapped[dict] = mapped_column(JSON, nullable=False)
    execution: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class VideoRow(Base):
    __tablename__ = "videos"

    video_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(nullable=False)
    organization_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class ProcessingJobRow(Base):
    __tablename__ = "processing_jobs"

    job_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    video_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    camera_id: Mapped[str] = mapped_column(String(100), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    organization_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    progress_percent: Mapped[float] = mapped_column(nullable=False)
    frames_processed: Mapped[int] = mapped_column(nullable=False)
    detections_found: Mapped[int] = mapped_column(nullable=False)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OrganizationRow(Base):
    __tablename__ = "organizations"
    organization_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    emergency_contact: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    notification_preference: Mapped[str] = mapped_column(String(100), nullable=False, default="dashboard")
    api_key_last_four: Mapped[str] = mapped_column(String(4), nullable=False, default="")
    api_key_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, default="")


class UserRow(Base):
    __tablename__ = "users"
    user_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False)


class SessionRow(Base):
    __tablename__ = "auth_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class CameraRow(Base):
    __tablename__ = "cameras"
    camera_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)


class KnowledgeDocumentRow(Base):
    __tablename__ = "knowledge_documents"
    document_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_name: Mapped[str] = mapped_column(String(255), nullable=False)
    page_count: Mapped[int] = mapped_column(nullable=False)
    chunk_count: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class KnowledgeChunkRow(Base):
    __tablename__ = "knowledge_chunks"
    chunk_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    position: Mapped[int] = mapped_column(nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)


class DeliveryRow(Base):
    __tablename__ = "deliveries"
    delivery_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    detection_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    action_kind: Mapped[str] = mapped_column(String(30), nullable=False)
    target: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    message: Mapped[str] = mapped_column(String(1000), nullable=False)
    provider_reference: Mapped[str] = mapped_column(String(100), nullable=False)
    report_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
