import hashlib

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from ..domain.models import (
    AgentAudit,
    DeliveryRecord,
    IncidentMemory,
    LearnedThresholdProfile,
    Severity,
)
from ..perception.models import ProcessingJob, ProcessingStatus, VideoAsset
from .models import (
    AgentAuditRow,
    DeliveryRow,
    IncidentRow,
    LearnedThresholdProfileRow,
    ProcessingJobRow,
    VideoRow,
)


class SqlAlchemyThresholdProfileRepository:
    """Persist one learned baseline per tenant and normalized camera location."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def get(self, organization_id: str | None, location: str) -> LearnedThresholdProfile | None:
        key = self._key(organization_id, location)
        with self.session_factory() as session:
            row = session.get(LearnedThresholdProfileRow, key)
            if row is None:
                return None
            return LearnedThresholdProfile(
                organization_id=row.organization_id,
                location=row.location,
                threshold=row.threshold,
                applied_review_versions=tuple(row.applied_review_versions),
                updated_at=row.updated_at,
            )

    def save(self, profile: LearnedThresholdProfile) -> None:
        key = self._key(profile.organization_id, profile.location)
        with self.session_factory.begin() as session:
            row = session.get(LearnedThresholdProfileRow, key) or LearnedThresholdProfileRow(
                profile_key=key
            )
            row.organization_id = profile.organization_id
            row.location = profile.location.strip()
            row.threshold = profile.threshold
            row.applied_review_versions = list(profile.applied_review_versions)
            row.updated_at = profile.updated_at
            session.add(row)

    @staticmethod
    def _key(organization_id: str | None, location: str) -> str:
        tenant = organization_id or "__local__"
        normalized_location = " ".join(location.strip().casefold().split())
        return hashlib.sha256(f"{tenant}|{normalized_location}".encode()).hexdigest()


class SqlAlchemyIncidentRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def save(self, memory: IncidentMemory) -> None:
        row = IncidentRow(
            incident_id=memory.incident_id,
            detection_id=memory.detection_id,
            severity=memory.severity.value,
            location=memory.location,
            rationale=list(memory.rationale),
            alert_message=memory.alert_message,
            organization_id=memory.organization_id,
            source_video_id=memory.source_video_id,
            frame_timestamp_ms=memory.frame_timestamp_ms,
            stored_at=memory.stored_at,
        )
        with self.session_factory.begin() as session:
            session.add(row)

    def get(self, incident_id: str, organization_id: str | None = None) -> IncidentMemory | None:
        with self.session_factory() as session:
            row = session.get(IncidentRow, incident_id)
            if (
                row is not None
                and organization_id is not None
                and row.organization_id != organization_id
            ):
                return None
            return self._to_domain(row) if row else None

    def list_recent(
        self, limit: int = 50, organization_id: str | None = None
    ) -> list[IncidentMemory]:
        statement = select(IncidentRow)
        if organization_id is not None:
            statement = statement.where(IncidentRow.organization_id == organization_id)
        statement = statement.order_by(IncidentRow.stored_at.desc()).limit(limit)
        with self.session_factory() as session:
            return [self._to_domain(row) for row in session.scalars(statement)]

    def severity_counts(self, organization_id: str | None = None) -> dict[str, int]:
        statement = select(IncidentRow.severity, func.count()).group_by(IncidentRow.severity)
        if organization_id is not None:
            statement = statement.where(IncidentRow.organization_id == organization_id)
        with self.session_factory() as session:
            return {severity: count for severity, count in session.execute(statement)}

    @staticmethod
    def _to_domain(row: IncidentRow) -> IncidentMemory:
        return IncidentMemory(
            incident_id=row.incident_id,
            detection_id=row.detection_id,
            severity=Severity(row.severity),
            location=row.location,
            rationale=tuple(row.rationale),
            alert_message=row.alert_message,
            organization_id=row.organization_id,
            source_video_id=row.source_video_id,
            frame_timestamp_ms=row.frame_timestamp_ms,
            stored_at=row.stored_at,
        )


class SqlAlchemyAgentAuditRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def save(self, audit: AgentAudit) -> None:
        with self.session_factory.begin() as session:
            session.add(AgentAuditRow(**audit.__dict__))

    def get_for_incident(self, incident_id: str) -> AgentAudit | None:
        statement = select(AgentAuditRow).where(AgentAuditRow.incident_id == incident_id)
        with self.session_factory() as session:
            row = session.scalar(statement)
            if row is None:
                return None
            return AgentAudit(
                **{
                    column.name: getattr(row, column.name)
                    for column in AgentAuditRow.__table__.columns
                }
            )


class SqlAlchemyVideoRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def save(self, asset: VideoAsset) -> None:
        with self.session_factory.begin() as session:
            session.add(
                VideoRow(
                    video_id=asset.video_id,
                    original_filename=asset.original_filename,
                    stored_name=asset.stored_name,
                    content_type=asset.content_type,
                    size_bytes=asset.size_bytes,
                    organization_id=asset.organization_id,
                    created_at=asset.created_at,
                )
            )

    def get(self, video_id: str, organization_id: str | None = None) -> VideoAsset | None:
        with self.session_factory() as session:
            row = session.get(VideoRow, video_id)
            if (
                row is not None
                and organization_id is not None
                and row.organization_id != organization_id
            ):
                return None
            return self._to_domain(row) if row else None

    def list_recent(self, limit: int = 50, organization_id: str | None = None) -> list[VideoAsset]:
        statement = select(VideoRow)
        if organization_id is not None:
            statement = statement.where(VideoRow.organization_id == organization_id)
        statement = statement.order_by(VideoRow.created_at.desc()).limit(limit)
        with self.session_factory() as session:
            return [self._to_domain(row) for row in session.scalars(statement)]

    @staticmethod
    def _to_domain(row: VideoRow) -> VideoAsset:
        return VideoAsset(
            video_id=row.video_id,
            original_filename=row.original_filename,
            stored_name=row.stored_name,
            content_type=row.content_type,
            size_bytes=row.size_bytes,
            organization_id=row.organization_id,
            created_at=row.created_at,
        )


class SqlAlchemyProcessingJobRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def save(self, job: ProcessingJob) -> None:
        with self.session_factory.begin() as session:
            row = session.get(ProcessingJobRow, job.job_id) or ProcessingJobRow(job_id=job.job_id)
            row.video_id = job.video_id
            row.camera_id = job.camera_id
            row.location = job.location
            row.organization_id = job.organization_id
            row.status = job.status.value
            row.progress_percent = job.progress_percent
            row.frames_processed = job.frames_processed
            row.detections_found = job.detections_found
            row.sensor_scenario = job.sensor_scenario
            row.latest_sensor_sample = job.latest_sensor_sample
            row.error_message = job.error_message
            row.created_at = job.created_at
            row.updated_at = job.updated_at
            session.add(row)

    def get(self, job_id: str) -> ProcessingJob | None:
        with self.session_factory() as session:
            row = session.get(ProcessingJobRow, job_id)
            if row is None:
                return None
            return ProcessingJob(
                job_id=row.job_id,
                video_id=row.video_id,
                camera_id=row.camera_id,
                location=row.location,
                organization_id=row.organization_id,
                status=ProcessingStatus(row.status),
                progress_percent=row.progress_percent,
                frames_processed=row.frames_processed,
                detections_found=row.detections_found,
                sensor_scenario=row.sensor_scenario,
                latest_sensor_sample=row.latest_sensor_sample,
                error_message=row.error_message,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )


class SqlAlchemyDeliveryRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def save(self, record: DeliveryRecord) -> None:
        with self.session_factory.begin() as session:
            session.add(DeliveryRow(**record.__dict__))

    def list_for_detection(self, detection_id: str) -> list[DeliveryRecord]:
        statement = (
            select(DeliveryRow)
            .where(DeliveryRow.detection_id == detection_id)
            .order_by(DeliveryRow.created_at)
        )
        with self.session_factory() as session:
            return [
                DeliveryRecord(
                    **{
                        column.name: getattr(row, column.name)
                        for column in DeliveryRow.__table__.columns
                    }
                )
                for row in session.scalars(statement)
            ]
