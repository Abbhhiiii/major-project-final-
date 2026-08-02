from pathlib import Path

import cv2

from packages.surveillance.perception.detectors import UltralyticsAccidentDetector
from packages.surveillance.perception.models import VideoFrame

MODEL_ROOT = Path("/Users/abhinavshetty/Accident-Detection-and-Notification/ML part")


def test_real_checkpoint_detects_repository_sample() -> None:
    detector = UltralyticsAccidentDetector(MODEL_ROOT / "best.pt", 0.5)
    image = cv2.imread(str(MODEL_ROOT / "inputs/images/image5.jpg"))
    assert image is not None
    outputs = detector.detect(
        VideoFrame(0, 0, image), camera_id="test-camera", location="Test Road"
    )
    assert len(outputs) >= 1
    assert outputs[0].confidence >= 0.5
    assert outputs[0].impact_score == 0.7
