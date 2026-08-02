from __future__ import annotations

from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import BinaryIO, Protocol

from .domain.models import (
    Action,
    AgentAudit,
    Decision,
    DeliveryRecord,
    Detection,
    IncidentContext,
    IncidentMemory,
    Verification,
)
from .perception.models import (
    DetectorOutput,
    ProcessingJob,
    VideoAsset,
    VideoFrame,
)


class ContextRepository(Protocol):
    def retrieve(self, detection: Detection) -> IncidentContext: ...


class ReasoningService(Protocol):
    def run(
        self, detection: Detection, verification: Verification, context: IncidentContext
    ) -> Decision: ...


class ActionExecutor(Protocol):
    def execute(self, action: Action) -> None: ...


class DeliveryRepository(Protocol):
    def save(self, record: DeliveryRecord) -> None: ...

    def list_for_detection(self, detection_id: str) -> Sequence[DeliveryRecord]: ...


class MemoryRepository(Protocol):
    def save(self, memory: IncidentMemory) -> None: ...

    def get(self, incident_id: str, organization_id: str | None = None) -> IncidentMemory | None: ...

    def list_recent(
        self, limit: int = 50, organization_id: str | None = None
    ) -> Sequence[IncidentMemory]: ...

    def severity_counts(self, organization_id: str | None = None) -> dict[str, int]: ...


class AuditRepository(Protocol):
    def save(self, audit: AgentAudit) -> None: ...

    def get_for_incident(self, incident_id: str) -> AgentAudit | None: ...


class VideoRepository(Protocol):
    def save(self, asset: VideoAsset) -> None: ...

    def get(self, video_id: str, organization_id: str | None = None) -> VideoAsset | None: ...

    def list_recent(self, limit: int = 50, organization_id: str | None = None) -> Sequence[VideoAsset]: ...


class VideoStorage(Protocol):
    def store(self, filename: str, content_type: str, source: BinaryIO) -> VideoAsset: ...

    def resolve(self, stored_name: str) -> Path: ...


class FrameReader(Protocol):
    def frames(self, path: Path, sample_fps: float) -> tuple[int, Iterator[VideoFrame]]: ...


class AccidentDetector(Protocol):
    def detect(
        self, frame: VideoFrame, *, camera_id: str, location: str
    ) -> Sequence[DetectorOutput]: ...


class ProcessingJobRepository(Protocol):
    def save(self, job: ProcessingJob) -> None: ...

    def get(self, job_id: str) -> ProcessingJob | None: ...
