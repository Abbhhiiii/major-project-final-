from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime

from ..domain.models import Detection, StageEvent
from ..orchestrator import IncidentOrchestrator
from ..perception.models import ProcessingJob, ProcessingStatus
from ..perception.normalization import DetectionNormalizer
from ..ports import (
    AccidentDetector,
    FrameReader,
    ProcessingJobRepository,
    VideoRepository,
    VideoStorage,
)

logger = logging.getLogger(__name__)


class VideoProcessingService:
    def __init__(
        self,
        videos: VideoRepository,
        storage: VideoStorage,
        jobs: ProcessingJobRepository,
        reader: FrameReader,
        detector: AccidentDetector,
        normalizer: DetectionNormalizer,
        orchestrator: IncidentOrchestrator,
        sample_fps: float = 2,
        playback_speed: float = 4,
        event_sink: Callable[[str, StageEvent], None] | None = None,
        temporal_cluster_gap_seconds: float = 5,
    ) -> None:
        self.videos = videos
        self.storage = storage
        self.jobs = jobs
        self.reader = reader
        self.detector = detector
        self.normalizer = normalizer
        self.orchestrator = orchestrator
        self.sample_fps = sample_fps
        self.playback_speed = playback_speed
        self.event_sink = event_sink
        self.temporal_cluster_gap_ms = round(temporal_cluster_gap_seconds * 1000)

    def create_job(
        self,
        video_id: str,
        camera_id: str,
        location: str,
        organization_id: str | None = None,
    ) -> ProcessingJob:
        if self.videos.get(video_id) is None:
            raise LookupError("Video not found")
        job = ProcessingJob(
            video_id=video_id,
            camera_id=camera_id,
            location=location,
            organization_id=organization_id,
        )
        self.jobs.save(job)
        return job

    def process(self, job_id: str) -> None:
        job = self.jobs.get(job_id)
        if job is None:
            return
        running = replace(job, status=ProcessingStatus.RUNNING, updated_at=datetime.now(UTC))
        self.jobs.save(running)
        try:
            video = self.videos.get(job.video_id)
            if video is None:
                raise LookupError("Video not found")
            total, frames = self.reader.frames(
                self.storage.resolve(video.stored_name), self.sample_fps
            )
            detections = 0
            candidates: list[Detection] = []
            previous_timestamp = 0
            for position, frame in enumerate(frames, start=1):
                latest = self.jobs.get(job_id)
                if latest is not None and latest.status == ProcessingStatus.CANCELLED:
                    return
                delay_ms = frame.timestamp_ms - previous_timestamp
                if self.playback_speed > 0 and delay_ms > 0:
                    time.sleep(delay_ms / 1000 / self.playback_speed)
                previous_timestamp = frame.timestamp_ms
                outputs = self.detector.detect(
                    frame, camera_id=job.camera_id, location=job.location
                )
                for output in outputs:
                    detection = self.normalizer.normalize(
                        job.video_id, job.camera_id, output, job.organization_id
                    )
                    candidates.append(detection)
                    detections += 1
                running = replace(
                    running,
                    progress_percent=round(position / max(total, 1) * 100, 1),
                    frames_processed=position,
                    detections_found=detections,
                    updated_at=datetime.now(UTC),
                )
                self.jobs.save(running)
            latest = self.jobs.get(job_id)
            if latest is not None and latest.status == ProcessingStatus.CANCELLED:
                return
            for cluster in self._temporal_clusters(candidates):
                primary = self._aggregate_cluster(cluster)
                self.orchestrator.process(
                    primary,
                    (
                        lambda event: self.event_sink(job.job_id, event)
                        if self.event_sink is not None
                        else None
                    ),
                )
            self.jobs.save(
                replace(
                    running,
                    status=ProcessingStatus.COMPLETED,
                    progress_percent=100,
                    updated_at=datetime.now(UTC),
                )
            )
        except Exception as error:
            logger.exception("Video processing failed", extra={"job_id": job_id})
            self.jobs.save(
                replace(
                    running,
                    status=ProcessingStatus.FAILED,
                    error_message=str(error),
                    updated_at=datetime.now(UTC),
                )
            )

    def _temporal_clusters(self, detections: list[Detection]) -> list[list[Detection]]:
        ordered = sorted(detections, key=lambda item: item.frame_timestamp_ms or 0)
        clusters: list[list[Detection]] = []
        for detection in ordered:
            timestamp = detection.frame_timestamp_ms or 0
            if not clusters:
                clusters.append([detection])
                continue
            previous_timestamp = clusters[-1][-1].frame_timestamp_ms or 0
            if timestamp - previous_timestamp <= self.temporal_cluster_gap_ms:
                clusters[-1].append(detection)
            else:
                clusters.append([detection])
        return clusters

    @staticmethod
    def _aggregate_cluster(cluster: list[Detection]) -> Detection:
        strongest = max(cluster, key=lambda item: (item.confidence, item.impact_score))
        return replace(
            strongest,
            confidence=max(item.confidence for item in cluster),
            impact_score=max(item.impact_score for item in cluster),
            vehicle_count=max(item.vehicle_count for item in cluster),
            stopped_vehicle=any(item.stopped_vehicle for item in cluster),
        )
