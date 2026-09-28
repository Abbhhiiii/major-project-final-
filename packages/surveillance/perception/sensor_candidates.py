from __future__ import annotations

from ..domain.models import SensorReading
from ..verification.fusion import effective_reliability


class SensorCandidateDetector:
    """Nominates sensor readings for verification without deciding the incident outcome."""

    def __init__(
        self,
        probability_threshold: float = 0.7,
        reliability_threshold: float = 0.5,
        freshness_half_life_ms: int = 10_000,
    ) -> None:
        self.probability_threshold = probability_threshold
        self.reliability_threshold = reliability_threshold
        self.freshness_half_life_ms = freshness_half_life_ms

    def detect(self, readings: tuple[SensorReading, ...]) -> tuple[str, ...]:
        return tuple(
            reading.sensor_type
            for reading in readings
            if reading.probability >= self.probability_threshold
            and effective_reliability(reading, self.freshness_half_life_ms)
            >= self.reliability_threshold
        )
