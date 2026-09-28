from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.exc import IntegrityError
from starlette.responses import FileResponse, StreamingResponse

from packages.surveillance.adapters import (
    InMemoryAuditRepository,
    InMemoryIncidentRepository,
    InMemoryThresholdProfileRepository,
    LocalContextRepository,
    RecordingActionExecutor,
)
from packages.surveillance.agents import (
    AuditAgent,
    ExecutionAgent,
    MemoryAgent,
    PlanningAgent,
    ReasoningAgent,
    RetrievalAgent,
    VerificationAgent,
)
from packages.surveillance.application.auth import (
    fingerprint_api_key,
    hash_password,
    verify_password,
)
from packages.surveillance.application.video_ingestion import VideoIngestionService
from packages.surveillance.application.video_processing import VideoProcessingService
from packages.surveillance.data.database import (
    create_database_engine,
    create_session_factory,
    upgrade_schema,
)
from packages.surveillance.data.onboarding_repository import OnboardingRepository
from packages.surveillance.data.repositories import (
    SqlAlchemyAgentAuditRepository,
    SqlAlchemyDeliveryRepository,
    SqlAlchemyIncidentRepository,
    SqlAlchemyProcessingJobRepository,
    SqlAlchemyThresholdProfileRepository,
    SqlAlchemyVideoRepository,
)
from packages.surveillance.data.review_memory import ReviewedContextRepository
from packages.surveillance.domain.models import Detection, SensorReading, structured
from packages.surveillance.domain.onboarding import Organization
from packages.surveillance.infrastructure.config import Settings, get_settings
from packages.surveillance.infrastructure.execution import ExecutionRouter, PdfReportRenderer
from packages.surveillance.infrastructure.geocoding import (
    GeocodingUnavailable,
    NominatimGeocoder,
)
from packages.surveillance.infrastructure.groq_reasoning import (
    GroqReasoningAgent,
    UnconfiguredReasoningAgent,
)
from packages.surveillance.infrastructure.job_events import JobEventBuffer
from packages.surveillance.infrastructure.video_storage import (
    InvalidVideoError,
    LocalVideoStorage,
)
from packages.surveillance.knowledge.pdf_ingestion import PolicyPdfIngestor
from packages.surveillance.orchestrator import IncidentOrchestrator
from packages.surveillance.perception.detectors import (
    UltralyticsAccidentDetector,
    UnconfiguredAccidentDetector,
)
from packages.surveillance.perception.frame_reader import OpenCVFrameReader
from packages.surveillance.perception.models import (
    DetectorOutput,
    ProcessingStatus,
    VideoAsset,
)
from packages.surveillance.perception.normalization import DetectionNormalizer
from packages.surveillance.perception.sensor_candidates import SensorCandidateDetector
from packages.surveillance.perception.synthetic_sensors import (
    SyntheticSensorStreamGenerator,
    SyntheticSensorStreamStore,
)
from packages.surveillance.ports import (
    AccidentDetector,
    ActionExecutor,
    AuditRepository,
    FrameReader,
    MemoryRepository,
    ReasoningService,
)
from packages.surveillance.verification import (
    AdaptiveThresholdModel,
    EvidenceFusionModel,
)


class SensorReadingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sensor_type: str = Field(min_length=1, max_length=50)
    probability: float = Field(ge=0, le=1)
    reliability: float = Field(default=1, ge=0, le=1)
    age_ms: int = Field(default=0, ge=0)
    source: str = Field(default="api", min_length=1, max_length=100)


class DetectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    camera_id: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    vehicle_count: int = Field(ge=0)
    stopped_vehicle: bool
    impact_score: float = Field(ge=0, le=1)
    location: str = Field(min_length=1)
    source_video_id: str | None = None
    frame_timestamp_ms: int | None = Field(default=None, ge=0)
    occurred_at: datetime | None = None
    sensor_readings: tuple[SensorReadingRequest, ...] = ()
    candidate_sources: tuple[str, ...] = ("visual",)


class DetectorOutputRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    camera_id: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    impact_score: float = Field(ge=0, le=1)
    vehicle_count: int = Field(ge=0)
    stopped_vehicle: bool
    frame_timestamp_ms: int = Field(ge=0)
    location: str = Field(min_length=1)


class ProcessingJobRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    camera_id: str = Field(min_length=1)
    location: str = Field(min_length=1)
    sensor_scenario: Literal["both_high", "both_low", "smoke_high", "audio_high", "randomized"] = (
        "randomized"
    )


class SignupRequest(BaseModel):
    organization_name: str = Field(min_length=2, max_length=255)
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: str
    password: str


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    severity: Literal["low", "medium", "high", "critical"]
    response_action: Literal["call", "message", "none"]
    reason: str = Field(min_length=10, max_length=2000)
    false_alarm: bool = False


class OnboardingRequest(BaseModel):
    camera_name: str = Field(min_length=2, max_length=255)
    camera_location: str = Field(min_length=2, max_length=255)
    emergency_contact: str = Field(min_length=3, max_length=255)
    notification_preference: str = "voice alert for high-severity incidents"
    agent_api_key: str = Field(min_length=8, max_length=500)

    @field_validator("emergency_contact")
    @classmethod
    def validate_emergency_contact(cls, value: str) -> str:
        return normalize_emergency_contact(value)


class EmergencyContactRequest(BaseModel):
    emergency_contact: str = Field(min_length=3, max_length=255)
    notification_preference: str = Field(min_length=3, max_length=100)

    @field_validator("emergency_contact")
    @classmethod
    def validate_emergency_contact(cls, value: str) -> str:
        return normalize_emergency_contact(value)


def normalize_emergency_contact(value: str) -> str:
    normalized = re.sub(r"[\s().-]", "", value)
    if not re.fullmatch(r"\+[1-9]\d{7,14}", normalized):
        raise ValueError("Use E.164 format, for example +919876543210")
    return normalized


def build_orchestrator(
    memory_repository: MemoryRepository | None = None,
    context_repository=None,
    action_executor: ActionExecutor | None = None,
    force_accept_verification: bool = False,
    reasoning_service: ReasoningService | None = None,
    audit_repository: AuditRepository | None = None,
    fusion_model: EvidenceFusionModel | None = None,
    simulation_mode: bool = False,
    adaptive_threshold: AdaptiveThresholdModel | None = None,
    threshold_profiles=None,
) -> IncidentOrchestrator:
    return IncidentOrchestrator(
        VerificationAgent(force_accept_verification, fusion_model),
        RetrievalAgent(context_repository or LocalContextRepository()),
        reasoning_service or ReasoningAgent(),
        PlanningAgent(simulation_mode),
        ExecutionAgent(action_executor or RecordingActionExecutor()),
        MemoryAgent(memory_repository or InMemoryIncidentRepository()),
        AuditAgent(audit_repository or InMemoryAuditRepository()),
        adaptive_threshold,
        threshold_profiles or InMemoryThresholdProfileRepository(),
    )


def create_app(
    settings: Settings | None = None,
    detector: AccidentDetector | None = None,
    frame_reader: FrameReader | None = None,
    reasoning_service: ReasoningService | None = None,
) -> FastAPI:
    runtime_settings = settings or get_settings()
    logging.basicConfig(
        level=runtime_settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    engine = create_database_engine(runtime_settings.database_url)
    session_factory = create_session_factory(engine)
    repository = SqlAlchemyIncidentRepository(session_factory)
    video_repository = SqlAlchemyVideoRepository(session_factory)
    job_repository = SqlAlchemyProcessingJobRepository(session_factory)
    threshold_profile_repository = SqlAlchemyThresholdProfileRepository(session_factory)
    onboarding_repository = OnboardingRepository(
        session_factory, runtime_settings.session_ttl_hours
    )
    delivery_repository = SqlAlchemyDeliveryRepository(session_factory)
    audit_repository = SqlAlchemyAgentAuditRepository(session_factory)
    video_storage = LocalVideoStorage(
        runtime_settings.upload_directory,
        runtime_settings.max_video_size_mb * 1024 * 1024,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        upgrade_schema(runtime_settings.database_url)
        try:
            yield
        finally:
            engine.dispose()

    application = FastAPI(title=runtime_settings.app_name, version="0.2.0", lifespan=lifespan)
    application.state.settings = runtime_settings
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(runtime_settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.state.engine = engine
    application.state.incidents = repository
    application.state.videos = video_repository
    application.state.video_storage = video_storage
    application.state.video_ingestion = VideoIngestionService(video_storage, video_repository)
    application.state.sensor_streams = SyntheticSensorStreamStore(
        runtime_settings.upload_directory / "generated_sensor_streams"
    )
    application.state.detection_normalizer = DetectionNormalizer()
    application.state.processing_jobs = job_repository
    application.state.onboarding = onboarding_repository
    application.state.review_memory = ReviewedContextRepository(
        session_factory, onboarding_repository
    )
    application.state.deliveries = delivery_repository
    application.state.audits = audit_repository
    application.state.policy_ingestor = PolicyPdfIngestor(runtime_settings.policy_directory)
    application.state.geocoder = NominatimGeocoder(
        runtime_settings.geocoding_base_url,
        runtime_settings.geocoding_user_agent,
    )
    application.state.job_events = JobEventBuffer()
    execution_router = ExecutionRouter(
        delivery_repository,
        PdfReportRenderer(runtime_settings.report_directory),
        twilio_enabled=runtime_settings.twilio_enabled,
        account_sid=runtime_settings.twilio_account_sid,
        auth_token=runtime_settings.twilio_auth_token,
        api_key_sid=runtime_settings.twilio_api_key_sid,
        api_key_secret=runtime_settings.twilio_api_key_secret,
        from_number=runtime_settings.twilio_from_number,
        whatsapp_enabled=runtime_settings.twilio_whatsapp_enabled,
        whatsapp_from_number=runtime_settings.twilio_whatsapp_from_number,
        vonage_whatsapp_enabled=runtime_settings.vonage_whatsapp_enabled,
        vonage_api_key=runtime_settings.vonage_api_key,
        vonage_api_secret=runtime_settings.vonage_api_secret,
        vonage_whatsapp_from_number=runtime_settings.vonage_whatsapp_from_number,
        vonage_messages_url=runtime_settings.vonage_messages_url,
        public_base_url=runtime_settings.public_base_url,
        report_link_secret=runtime_settings.report_link_secret,
        execution_mode=runtime_settings.execution_mode,
    )
    configured_reasoning = reasoning_service
    if configured_reasoning is None and runtime_settings.groq_api_key:
        configured_reasoning = GroqReasoningAgent(
            runtime_settings.groq_api_key,
            runtime_settings.groq_model,
            max_retries=runtime_settings.groq_max_retries,
            allow_missing_contact=runtime_settings.execution_mode == "simulate",
        )
    application.state.orchestrator = build_orchestrator(
        repository,
        application.state.review_memory,
        execution_router,
        runtime_settings.force_accept_verification,
        configured_reasoning or UnconfiguredReasoningAgent(),
        audit_repository,
        EvidenceFusionModel(
            threshold=runtime_settings.verification_threshold,
            override_probability=runtime_settings.sensor_override_probability,
            override_reliability=runtime_settings.sensor_override_reliability,
            visual_override_impact=runtime_settings.visual_override_impact,
            visual_override_confidence=runtime_settings.visual_override_confidence,
        ),
        simulation_mode=runtime_settings.execution_mode == "simulate",
        adaptive_threshold=AdaptiveThresholdModel(
            minimum=runtime_settings.adaptive_threshold_minimum,
            maximum=runtime_settings.adaptive_threshold_maximum,
            maximum_adjustment=runtime_settings.adaptive_threshold_maximum_adjustment,
            stabilizer=runtime_settings.adaptive_threshold_stabilizer,
            recency_half_life_days=runtime_settings.adaptive_threshold_recency_half_life_days,
        ),
        threshold_profiles=threshold_profile_repository,
    )
    configured_detector = detector
    if configured_detector is None and runtime_settings.accident_model_path is not None:
        configured_detector = UltralyticsAccidentDetector(
            runtime_settings.accident_model_path,
            runtime_settings.accident_confidence_threshold,
        )
    application.state.video_processor = VideoProcessingService(
        videos=video_repository,
        storage=video_storage,
        jobs=job_repository,
        reader=frame_reader or OpenCVFrameReader(),
        detector=configured_detector or UnconfiguredAccidentDetector(),
        normalizer=application.state.detection_normalizer,
        orchestrator=application.state.orchestrator,
        sample_fps=runtime_settings.frame_sample_fps,
        playback_speed=runtime_settings.playback_speed,
        event_sink=application.state.job_events.append,
        temporal_cluster_gap_seconds=runtime_settings.temporal_cluster_gap_seconds,
        sensor_candidate_detector=SensorCandidateDetector(
            probability_threshold=runtime_settings.sensor_candidate_probability,
            reliability_threshold=runtime_settings.sensor_candidate_reliability,
        ),
        sensor_generator=SyntheticSensorStreamGenerator(),
        sensor_stream_store=application.state.sensor_streams,
        sensor_event_sink=application.state.job_events.append_sensor,
    )
    register_routes(application)
    twilio_configured = bool(
        runtime_settings.twilio_enabled
        and runtime_settings.twilio_account_sid
        and runtime_settings.twilio_from_number
        and (
            runtime_settings.twilio_auth_token
            or (runtime_settings.twilio_api_key_sid and runtime_settings.twilio_api_key_secret)
        )
    )
    vonage_configured = bool(
        runtime_settings.vonage_whatsapp_enabled
        and runtime_settings.vonage_api_key
        and runtime_settings.vonage_api_secret
        and runtime_settings.vonage_whatsapp_from_number
    )
    twilio_whatsapp_configured = bool(
        twilio_configured
        and runtime_settings.twilio_whatsapp_enabled
        and runtime_settings.twilio_whatsapp_from_number
        and runtime_settings.public_base_url
        and runtime_settings.report_link_secret
        and runtime_settings.twilio_whatsapp_live_validated
    )
    external_execution_ready = (
        runtime_settings.execution_mode == "simulate"
        or (runtime_settings.execution_mode == "hybrid" and vonage_configured)
        or (
            runtime_settings.execution_mode == "live"
            and twilio_configured
            and runtime_settings.twilio_live_validated
            and (vonage_configured or twilio_whatsapp_configured)
        )
    )
    application.state.integration_status = {
        "accident_model": isinstance(configured_detector, UltralyticsAccidentDetector),
        "policy_rag": True,
        "pdf_reports": True,
        "execution_mode": runtime_settings.execution_mode,
        "external_execution": external_execution_ready,
        "twilio_configured": twilio_configured,
        "twilio_voice": twilio_configured and runtime_settings.twilio_live_validated,
        "twilio_whatsapp": twilio_whatsapp_configured,
        "vonage_whatsapp": vonage_configured,
        "voice_execution_simulated": runtime_settings.execution_mode in {"simulate", "hybrid"},
        "model_backed_reasoning": isinstance(configured_reasoning, GroqReasoningAgent),
        "reasoning_provider": "groq"
        if isinstance(configured_reasoning, GroqReasoningAgent)
        else "unconfigured",
        "reasoning_model": runtime_settings.groq_model
        if isinstance(configured_reasoning, GroqReasoningAgent)
        else "",
        "forced_accept_verification": runtime_settings.force_accept_verification,
    }
    return application


def register_routes(application: FastAPI) -> None:
    @application.get("/api/v1/locations/search")
    def search_locations(
        request: Request,
        q: Annotated[str, Query(min_length=2, max_length=200)],
    ) -> dict[str, object]:
        require_session(request)
        try:
            return {"items": request.app.state.geocoder.search(q)}
        except GeocodingUnavailable as error:
            raise HTTPException(status_code=502, detail=str(error)) from error

    @application.get("/api/v1/locations/reverse")
    def reverse_location(
        request: Request,
        latitude: Annotated[float, Query(ge=-90, le=90)],
        longitude: Annotated[float, Query(ge=-180, le=180)],
    ) -> dict[str, object]:
        require_session(request)
        try:
            return request.app.state.geocoder.reverse(latitude, longitude)
        except GeocodingUnavailable as error:
            raise HTTPException(status_code=502, detail=str(error)) from error

    @application.get("/api/v1/incidents/{incident_id}/review")
    def get_review(request: Request, incident_id: str):
        session = require_session(request)
        if request.app.state.incidents.get(incident_id, session.organization_id) is None:
            raise HTTPException(404, "Incident not found")
        return request.app.state.review_memory.get(incident_id, session.organization_id)

    @application.put("/api/v1/incidents/{incident_id}/review")
    def save_review(request: Request, incident_id: str, payload: ReviewRequest):
        session = require_session(request)
        if request.app.state.incidents.get(incident_id, session.organization_id) is None:
            raise HTTPException(404, "Incident not found")
        if payload.false_alarm and payload.response_action != "none":
            raise HTTPException(422, "False alarms must use no escalation")
        return request.app.state.review_memory.save(
            incident_id, session.organization_id, session.user_id, payload.model_dump()
        )

    @application.post("/api/v1/auth/signup", status_code=201)
    def signup(request: Request, payload: SignupRequest) -> dict[str, object]:
        organization = Organization(name=payload.organization_name)
        try:
            session = request.app.state.onboarding.create_account(
                organization, payload.email, hash_password(payload.password)
            )
        except IntegrityError as error:
            raise HTTPException(
                status_code=409, detail="An account with this email already exists"
            ) from error
        return {
            "access_token": session.token,
            "token_type": "bearer",
            "organization_id": session.organization_id,
        }

    @application.post("/api/v1/auth/login")
    def login(request: Request, payload: LoginRequest) -> dict[str, object]:
        user = request.app.state.onboarding.find_user(payload.email)
        if user is None or not verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        session = request.app.state.onboarding.create_session(user)
        return {
            "access_token": session.token,
            "token_type": "bearer",
            "organization_id": session.organization_id,
        }

    @application.post("/api/v1/auth/logout", status_code=204)
    def logout(request: Request) -> None:
        session = require_session(request)
        request.app.state.onboarding.revoke_session(session.token)

    @application.get("/api/v1/onboarding")
    def onboarding_summary(request: Request) -> dict[str, object]:
        session = require_session(request)
        return request.app.state.onboarding.summary(session.organization_id)

    @application.put("/api/v1/onboarding")
    def configure_onboarding(request: Request, payload: OnboardingRequest) -> dict[str, object]:
        session = require_session(request)
        fingerprint, last_four = fingerprint_api_key(payload.agent_api_key)
        request.app.state.onboarding.configure(
            session.organization_id,
            str(uuid4()),
            payload.camera_name,
            payload.camera_location,
            payload.emergency_contact,
            payload.notification_preference,
            fingerprint,
            last_four,
        )
        return request.app.state.onboarding.summary(session.organization_id)

    @application.put("/api/v1/onboarding/emergency-contact")
    def update_emergency_contact(
        request: Request, payload: EmergencyContactRequest
    ) -> dict[str, object]:
        session = require_session(request)
        request.app.state.onboarding.update_emergency_contact(
            session.organization_id,
            payload.emergency_contact,
            payload.notification_preference,
        )
        return request.app.state.onboarding.summary(session.organization_id)

    @application.post("/api/v1/knowledge/policies", status_code=201)
    def upload_policy(request: Request, policy: Annotated[UploadFile, File()]) -> dict[str, object]:
        session = require_session(request)
        try:
            document, chunks = request.app.state.policy_ingestor.ingest(
                session.organization_id, policy.filename or "policy.pdf", policy.file
            )
        except (ValueError, OSError) as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        request.app.state.onboarding.save_document(document, chunks)
        return structured(document)

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/ready")
    def readiness(request: Request) -> dict[str, object]:
        integrations = request.app.state.integration_status
        required_ready = all(
            integrations[key]
            for key in (
                "accident_model",
                "policy_rag",
                "pdf_reports",
                "external_execution",
                "model_backed_reasoning",
            )
        )
        return {"ready": required_ready, "integrations": integrations}

    @application.post("/api/v1/incidents/process")
    def process_incident(request: Request, payload: DetectionRequest) -> dict[str, object]:
        session = require_session(request)
        values = payload.model_dump(exclude_none=True)
        values["sensor_readings"] = tuple(
            SensorReading(**reading) for reading in values["sensor_readings"]
        )
        values["organization_id"] = session.organization_id
        result = request.app.state.orchestrator.process(Detection(**values))
        return structured(result)

    @application.post("/api/v1/incidents/process/stream")
    def stream_incident(request: Request, payload: DetectionRequest) -> StreamingResponse:
        session = require_session(request)
        values = payload.model_dump(exclude_none=True)
        values["sensor_readings"] = tuple(
            SensorReading(**reading) for reading in values["sensor_readings"]
        )
        values["organization_id"] = session.organization_id
        detection = Detection(**values)

        def generate_events():
            for event in request.app.state.orchestrator.stream(detection):
                data = json.dumps(structured(event), separators=(",", ":"))
                yield f"event: {event.stage.value}\ndata: {data}\n\n"

        return StreamingResponse(generate_events(), media_type="text/event-stream")

    @application.get("/api/v1/incidents")
    def list_incidents(
        request: Request, limit: int = Query(default=50, ge=1, le=200)
    ) -> dict[str, object]:
        session = require_session(request)
        incidents = request.app.state.incidents.list_recent(limit, session.organization_id)
        return {"items": [structured(item) for item in incidents], "count": len(incidents)}

    @application.get("/api/v1/incidents/{incident_id}")
    def get_incident(request: Request, incident_id: str) -> dict[str, object]:
        session = require_session(request)
        incident = request.app.state.incidents.get(incident_id, session.organization_id)
        if incident is None:
            raise HTTPException(status_code=404, detail="Incident not found")
        return structured(incident)

    @application.get("/api/v1/incidents/{incident_id}/deliveries")
    def incident_deliveries(request: Request, incident_id: str) -> dict[str, object]:
        session = require_session(request)
        incident = request.app.state.incidents.get(incident_id, session.organization_id)
        if incident is None:
            raise HTTPException(status_code=404, detail="Incident not found")
        records = request.app.state.deliveries.list_for_detection(incident.detection_id)
        return {"items": [structured(record) for record in records], "count": len(records)}

    @application.get("/api/v1/incidents/{incident_id}/audit")
    def incident_audit(request: Request, incident_id: str) -> dict[str, object]:
        session = require_session(request)
        if request.app.state.incidents.get(incident_id, session.organization_id) is None:
            raise HTTPException(status_code=404, detail="Incident not found")
        audit = request.app.state.audits.get_for_incident(incident_id)
        if audit is None:
            raise HTTPException(status_code=404, detail="Agent audit not found")
        return structured(audit)

    @application.get("/api/v1/incidents/{incident_id}/report")
    def download_incident_report(request: Request, incident_id: str) -> FileResponse:
        session = require_session(request)
        incident = request.app.state.incidents.get(incident_id, session.organization_id)
        if incident is None:
            raise HTTPException(status_code=404, detail="Incident not found")
        records = request.app.state.deliveries.list_for_detection(incident.detection_id)
        report = next((record for record in records if record.report_path), None)
        if report is None or not Path(report.report_path).is_file():
            raise HTTPException(status_code=404, detail="Incident report not found")
        return FileResponse(
            report.report_path, media_type="application/pdf", filename=f"incident-{incident_id}.pdf"
        )

    @application.api_route("/api/v1/public/reports/{detection_id}.pdf", methods=["GET", "HEAD"])
    def public_incident_report(request: Request, detection_id: str, token: str) -> FileResponse:
        secret = request.app.state.settings.report_link_secret
        expected = (
            hmac.new(secret.encode(), detection_id.encode(), hashlib.sha256).hexdigest()
            if secret
            else ""
        )
        if not expected or not hmac.compare_digest(token, expected):
            raise HTTPException(status_code=403, detail="Invalid report link")
        path = (
            request.app.state.settings.report_directory.resolve() / f"incident-{detection_id}.pdf"
        )
        if not path.is_file():
            raise HTTPException(status_code=404, detail="Incident report not found")
        return FileResponse(path, media_type="application/pdf", filename="sentrix-report.pdf")

    @application.get("/api/v1/analytics/summary")
    def analytics_summary(request: Request) -> dict[str, object]:
        session = require_session(request)
        counts = request.app.state.incidents.severity_counts(session.organization_id)
        return {"total_incidents": sum(counts.values()), "by_severity": counts}

    @application.post("/api/v1/videos", status_code=201)
    def upload_video(request: Request, video: Annotated[UploadFile, File()]) -> dict[str, object]:
        session = require_session(request)
        try:
            asset = request.app.state.video_ingestion.ingest(
                video.filename or "video",
                video.content_type or "",
                video.file,
                session.organization_id,
            )
        except InvalidVideoError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return video_response(asset)

    @application.get("/api/v1/videos")
    def list_videos(
        request: Request, limit: int = Query(default=50, ge=1, le=200)
    ) -> dict[str, object]:
        session = require_session(request)
        videos = request.app.state.videos.list_recent(limit, session.organization_id)
        return {"items": [video_response(video) for video in videos], "count": len(videos)}

    @application.get("/api/v1/videos/{video_id}/content")
    def play_video(request: Request, video_id: str) -> FileResponse:
        session = require_session(request)
        asset = require_video(request, video_id, session.organization_id)
        path = request.app.state.video_storage.resolve(asset.stored_name)
        if not path.is_file():
            raise HTTPException(status_code=404, detail="Video content not found")
        return FileResponse(path, media_type=asset.content_type)

    @application.get("/api/v1/videos/{video_id}/sensor-stream")
    def download_generated_sensor_stream(request: Request, video_id: str) -> FileResponse:
        session = require_session(request)
        require_video(request, video_id, session.organization_id)
        path = request.app.state.sensor_streams.path_for(video_id)
        if not path.is_file():
            raise HTTPException(
                status_code=409,
                detail="Sensor stream is generated only after video processing completes",
            )
        return FileResponse(
            path,
            media_type="application/json",
            filename=f"sentrix-sensor-stream-{video_id[:8]}.json",
        )

    @application.post("/api/v1/videos/{video_id}/detections")
    def process_detector_output(
        request: Request, video_id: str, payload: DetectorOutputRequest
    ) -> dict[str, object]:
        session = require_session(request)
        require_video(request, video_id, session.organization_id)
        values = payload.model_dump()
        camera_id = values.pop("camera_id")
        detection = request.app.state.detection_normalizer.normalize(
            video_id,
            camera_id,
            DetectorOutput(**values),
            session.organization_id,
        )
        return structured(request.app.state.orchestrator.process(detection))

    @application.post("/api/v1/videos/{video_id}/process", status_code=202)
    def start_video_processing(
        request: Request,
        video_id: str,
        payload: ProcessingJobRequest,
        background_tasks: BackgroundTasks,
    ) -> dict[str, object]:
        session = require_session(request)
        try:
            require_video(request, video_id, session.organization_id)
            job = request.app.state.video_processor.create_job(
                video_id,
                payload.camera_id,
                payload.location,
                session.organization_id,
                payload.sensor_scenario,
            )
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        background_tasks.add_task(request.app.state.video_processor.process, job.job_id)
        return structured(job)

    @application.get("/api/v1/processing-jobs/{job_id}")
    def get_processing_job(request: Request, job_id: str) -> dict[str, object]:
        session = require_session(request)
        job = request.app.state.processing_jobs.get(job_id)
        if job is None or job.organization_id != session.organization_id:
            raise HTTPException(status_code=404, detail="Processing job not found")
        return structured(job)

    @application.post("/api/v1/processing-jobs/{job_id}/cancel")
    def cancel_processing_job(request: Request, job_id: str) -> dict[str, object]:
        session = require_session(request)
        job = request.app.state.processing_jobs.get(job_id)
        if job is None or job.organization_id != session.organization_id:
            raise HTTPException(status_code=404, detail="Processing job not found")
        if job.status not in {ProcessingStatus.QUEUED, ProcessingStatus.RUNNING}:
            raise HTTPException(status_code=409, detail="Only active jobs can be cancelled")
        cancelled = replace(
            job, status=ProcessingStatus.CANCELLED, updated_at=datetime.now(job.updated_at.tzinfo)
        )
        request.app.state.processing_jobs.save(cancelled)
        return structured(cancelled)

    @application.post("/api/v1/processing-jobs/{job_id}/retry", status_code=202)
    def retry_processing_job(
        request: Request, job_id: str, background_tasks: BackgroundTasks
    ) -> dict[str, object]:
        session = require_session(request)
        job = request.app.state.processing_jobs.get(job_id)
        if job is None or job.organization_id != session.organization_id:
            raise HTTPException(status_code=404, detail="Processing job not found")
        if job.status not in {ProcessingStatus.FAILED, ProcessingStatus.CANCELLED}:
            raise HTTPException(
                status_code=409, detail="Only failed or cancelled jobs can be retried"
            )
        retried = request.app.state.video_processor.create_job(
            job.video_id,
            job.camera_id,
            job.location,
            session.organization_id,
            job.sensor_scenario,
        )
        background_tasks.add_task(request.app.state.video_processor.process, retried.job_id)
        return structured(retried)

    @application.get("/api/v1/processing-jobs/{job_id}/events")
    def stream_processing_job(request: Request, job_id: str) -> StreamingResponse:
        session = require_session(request)
        initial_job = request.app.state.processing_jobs.get(job_id)
        if initial_job is None or initial_job.organization_id != session.organization_id:
            raise HTTPException(status_code=404, detail="Processing job not found")

        async def generate_job_events():
            last_update = None
            pipeline_position = 0
            sensor_position = 0
            while True:
                job = request.app.state.processing_jobs.get(job_id)
                if job is None:
                    break
                marker = job.updated_at.isoformat()
                pipeline_events = request.app.state.job_events.after(job_id, pipeline_position)
                sensor_frames = request.app.state.job_events.sensors_after(job_id, sensor_position)
                for sensor_frame in sensor_frames:
                    data = json.dumps(structured(sensor_frame), separators=(",", ":"))
                    yield f"event: sensor\ndata: {data}\n\n"
                sensor_position += len(sensor_frames)
                for pipeline_event in pipeline_events:
                    data = json.dumps(structured(pipeline_event), separators=(",", ":"))
                    yield f"event: pipeline\ndata: {data}\n\n"
                pipeline_position += len(pipeline_events)
                if marker != last_update:
                    data = json.dumps(structured(job), separators=(",", ":"))
                    yield f"event: progress\ndata: {data}\n\n"
                    last_update = marker
                if job.status in {
                    ProcessingStatus.COMPLETED,
                    ProcessingStatus.FAILED,
                    ProcessingStatus.CANCELLED,
                }:
                    break
                await asyncio.sleep(0.25)

        return StreamingResponse(generate_job_events(), media_type="text/event-stream")


def require_video(request: Request, video_id: str, organization_id: str) -> VideoAsset:
    asset = request.app.state.videos.get(video_id, organization_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Video not found")
    return asset


def optional_session(request: Request):
    authorization = request.headers.get("authorization", "")
    if not authorization.lower().startswith("bearer "):
        return None
    return request.app.state.onboarding.session_for_token(authorization.split(" ", 1)[1])


def require_session(request: Request):
    session = optional_session(request)
    if session is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return session


def video_response(asset: VideoAsset) -> dict[str, object]:
    return {
        "video_id": asset.video_id,
        "original_filename": asset.original_filename,
        "content_type": asset.content_type,
        "size_bytes": asset.size_bytes,
        "created_at": asset.created_at.isoformat(),
        "playback_path": f"/api/v1/videos/{asset.video_id}/content",
    }


app = create_app()
