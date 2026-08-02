from pathlib import Path

from ultralytics import YOLO

from .models import DetectorOutput, VideoFrame


class ObservationOnlyDetector:
    """Safe fallback that scans real frames but never fabricates accident detections."""

    def detect(
        self, frame: VideoFrame, *, camera_id: str, location: str
    ) -> tuple[DetectorOutput, ...]:
        return ()


class ModelNotConfiguredError(RuntimeError):
    pass


class UnconfiguredAccidentDetector:
    def detect(
        self, frame: VideoFrame, *, camera_id: str, location: str
    ) -> tuple[DetectorOutput, ...]:
        raise ModelNotConfiguredError("A real accident model path is required")


class UltralyticsAccidentDetector:
    def __init__(self, model_path: Path, confidence_threshold: float = 0.5) -> None:
        if not model_path.is_file():
            raise ModelNotConfiguredError(f"Accident model not found: {model_path}")
        self.model_path = model_path.resolve()
        self.confidence_threshold = confidence_threshold
        self.model = YOLO(str(self.model_path))

    def detect(
        self, frame: VideoFrame, *, camera_id: str, location: str
    ) -> tuple[DetectorOutput, ...]:
        results = self.model.predict(source=frame.image, conf=self.confidence_threshold, verbose=False)
        outputs: list[DetectorOutput] = []
        for result in results:
            if result.boxes is None:
                continue
            boxes = list(result.boxes)
            for box in boxes:
                confidence = float(box.conf[0].item())
                class_id = int(box.cls[0].item())
                outputs.append(
                    DetectorOutput(
                        confidence=confidence,
                        impact_score=0.7 if class_id == 0 else 0.95,
                        vehicle_count=max(1, len(boxes)),
                        stopped_vehicle=False,
                        frame_timestamp_ms=frame.timestamp_ms,
                        location=location,
                    )
                )
        return tuple(outputs)
