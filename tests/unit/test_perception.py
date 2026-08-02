import pytest

from packages.surveillance.perception.models import DetectorOutput
from packages.surveillance.perception.normalization import DetectionNormalizer


def test_detector_output_is_normalized_with_video_and_frame_context() -> None:
    detection = DetectionNormalizer().normalize(
        "video-1",
        "camera-1",
        DetectorOutput(0.91, 0.85, 2, True, 8300, "Ring Road"),
    )
    assert detection.source_video_id == "video-1"
    assert detection.frame_timestamp_ms == 8300
    assert detection.confidence == 0.91


def test_normalizer_rejects_invalid_provider_confidence() -> None:
    with pytest.raises(ValueError, match="between 0 and 1"):
        DetectionNormalizer().normalize(
            "video-1",
            "camera-1",
            DetectorOutput(1.4, 0.85, 2, True, 8300, "Ring Road"),
        )
