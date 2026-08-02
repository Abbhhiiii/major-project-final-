from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class VideoAsset:
    video_id: str
    original_filename: str
    stored_name: str
    content_type: str
    size_bytes: int
    organization_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class DetectorOutput:
    """Provider-neutral output produced by an accident-model adapter."""

    confidence: float
    impact_score: float
    vehicle_count: int
    stopped_vehicle: bool
    frame_timestamp_ms: int
    location: str


@dataclass(frozen=True)
class VideoFrame:
    index: int
    timestamp_ms: int
    image: Any


class ProcessingStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class ProcessingJob:
    video_id: str
    camera_id: str
    location: str
    organization_id: str | None = None
    status: ProcessingStatus = ProcessingStatus.QUEUED
    progress_percent: float = 0
    frames_processed: int = 0
    detections_found: int = 0
    error_message: str | None = None
    job_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
