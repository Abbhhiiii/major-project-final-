from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class SensorReading:
    """A normalized auxiliary-sensor probability with data-quality metadata."""

    sensor_type: str
    probability: float
    reliability: float = 1.0
    age_ms: int = 0
    source: str = "sensor"

    def __post_init__(self) -> None:
        if not 0 <= self.probability <= 1:
            raise ValueError("sensor probability must be between 0 and 1")
        if not 0 <= self.reliability <= 1:
            raise ValueError("sensor reliability must be between 0 and 1")
        if self.age_ms < 0:
            raise ValueError("sensor age_ms cannot be negative")


@dataclass(frozen=True)
class SensorFrameSample:
    """Synthetic auxiliary-sensor readings synchronized to one decoded video frame."""

    frame_index: int
    timestamp_ms: int
    readings: tuple[SensorReading, ...]

    def __post_init__(self) -> None:
        if self.frame_index < 0 or self.timestamp_ms < 0:
            raise ValueError("sensor frame index and timestamp must be non-negative")
        if not self.readings:
            raise ValueError("sensor frame sample requires at least one reading")


class Stage(StrEnum):
    DETECTION = "detection"
    VERIFICATION = "verification"
    RETRIEVAL = "context_retrieval"
    REASONING = "reasoning"
    PLANNING = "planning"
    EXECUTION = "execution"
    MEMORY = "memory"


@dataclass(frozen=True)
class Detection:
    camera_id: str
    confidence: float
    vehicle_count: int
    stopped_vehicle: bool
    impact_score: float
    location: str
    organization_id: str | None = None
    source_video_id: str | None = None
    frame_timestamp_ms: int | None = None
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    detection_id: str = field(default_factory=lambda: str(uuid4()))
    sensor_readings: tuple[SensorReading, ...] = ()
    sensor_timeline: tuple[SensorFrameSample, ...] = ()
    sensor_scenario: str = ""
    candidate_sources: tuple[str, ...] = ("visual",)

    def __post_init__(self) -> None:
        if not 0 <= self.confidence <= 1 or not 0 <= self.impact_score <= 1:
            raise ValueError("confidence and impact_score must be between 0 and 1")
        if self.vehicle_count < 0:
            raise ValueError("vehicle_count cannot be negative")
        if self.frame_timestamp_ms is not None and self.frame_timestamp_ms < 0:
            raise ValueError("frame_timestamp_ms cannot be negative")


@dataclass(frozen=True)
class Verification:
    detection_id: str
    verified: bool
    score: float
    evidence: tuple[str, ...]
    fused_probability: float = 0.0
    decision_threshold: float = 0.68
    override_source: str | None = None
    contributions: dict[str, float] = field(default_factory=dict)
    forced_accept: bool = False
    base_decision_threshold: float = 0.68
    threshold_adjustment: float = 0.0
    threshold_minimum: float = 0.60
    threshold_maximum: float = 0.76
    threshold_stabilizer: float = 3.0
    threshold_maximum_adjustment: float = 0.08
    threshold_factors: tuple[dict[str, Any], ...] = ()
    baseline_verified: bool = False
    adaptive_verified: bool = False
    default_decision_threshold: float = 0.68
    threshold_profile_updated: bool = False
    threshold_new_review_count: int = 0
    threshold_applied_review_versions: tuple[str, ...] = ()


@dataclass(frozen=True)
class LearnedThresholdProfile:
    organization_id: str
    location: str
    threshold: float
    applied_review_versions: tuple[str, ...] = ()
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class RetrievedEvidence:
    document_id: str
    filename: str
    chunk_position: int
    score: float
    excerpt: str


@dataclass(frozen=True)
class IncidentContext:
    policies: tuple[str, ...]
    contacts: tuple[str, ...]
    procedures: tuple[str, ...]
    prior_incident_count: int
    preferences: tuple[str, ...] = ()
    evidence: tuple[RetrievedEvidence, ...] = ()
    reviewed_incidents: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class Decision:
    severity: Severity
    rationale: tuple[str, ...]
    notify_emergency_services: bool
    alert_message: str
    provider: str = "deterministic"
    model: str = "rule-based"
    response_action: str | None = None
    memory_influence: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Action:
    kind: str
    target: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class IncidentPlan:
    actions: tuple[Action, ...]


@dataclass(frozen=True)
class ExecutionResult:
    successful_actions: tuple[str, ...]
    failed_actions: tuple[str, ...] = ()


@dataclass(frozen=True)
class DeliveryRecord:
    detection_id: str
    action_kind: str
    target: str
    status: str
    message: str
    provider_reference: str = ""
    report_path: str = ""
    delivery_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class IncidentMemory:
    incident_id: str
    detection_id: str
    severity: Severity
    location: str
    rationale: tuple[str, ...]
    alert_message: str
    organization_id: str | None = None
    source_video_id: str | None = None
    frame_timestamp_ms: int | None = None
    stored_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class AgentAudit:
    incident_id: str
    detection_id: str
    reasoning_provider: str
    reasoning_model: str
    retrieval: dict[str, Any]
    decision: dict[str, Any]
    plan: dict[str, Any]
    execution: dict[str, Any]
    audit_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class StageEvent:
    stage: Stage
    payload: dict[str, Any]


@dataclass(frozen=True)
class PipelineResult:
    incident_id: str
    status: str
    events: tuple[StageEvent, ...]


def _json_safe(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return _json_safe(asdict(value))
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, StrEnum):
        return value.value
    return value


def structured(value: Any) -> dict[str, Any]:
    """Convert a domain dataclass into a recursively JSON-safe dictionary."""
    result = _json_safe(value)
    if not isinstance(result, dict):
        raise TypeError("structured() expects a dataclass or mapping")
    return result
