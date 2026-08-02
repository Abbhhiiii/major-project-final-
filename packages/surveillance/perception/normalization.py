from ..domain.models import Detection
from .models import DetectorOutput


class DetectionNormalizer:
    """Validates provider output and translates it into the core detection contract."""

    def normalize(
        self,
        video_id: str,
        camera_id: str,
        output: DetectorOutput,
        organization_id: str | None = None,
    ) -> Detection:
        return Detection(
            camera_id=camera_id,
            confidence=output.confidence,
            vehicle_count=output.vehicle_count,
            stopped_vehicle=output.stopped_vehicle,
            impact_score=output.impact_score,
            location=output.location,
            organization_id=organization_id,
            source_video_id=video_id,
            frame_timestamp_ms=output.frame_timestamp_ms,
        )
