from __future__ import annotations

import math
from dataclasses import dataclass
from typing import ClassVar

from ..domain.models import Detection, SensorReading


def effective_reliability(reading: SensorReading, half_life_ms: int = 10_000) -> float:
    freshness = math.exp(-math.log(2) * reading.age_ms / max(half_life_ms, 1))
    return reading.reliability * freshness


@dataclass(frozen=True)
class FusionResult:
    probability: float
    verified: bool
    threshold: float
    override_source: str | None
    contributions: dict[str, float]
    evidence: tuple[str, ...]


class EvidenceFusionModel:
    """Reliability-aware logistic fusion for visual and auxiliary risk evidence.

    Coefficients are explicit demo priors and should be recalibrated with labeled
    synchronized sensor data before production use.
    """

    SENSOR_WEIGHTS: ClassVar[dict[str, float]] = {"smoke": 3.2, "audio": 2.8}

    def __init__(
        self,
        threshold: float = 0.68,
        override_probability: float = 0.92,
        override_reliability: float = 0.8,
        freshness_half_life_ms: int = 10_000,
        visual_override_impact: float = 0.9,
        visual_override_confidence: float = 0.75,
    ) -> None:
        self.threshold = threshold
        self.override_probability = override_probability
        self.override_reliability = override_reliability
        self.freshness_half_life_ms = freshness_half_life_ms
        self.visual_override_impact = visual_override_impact
        self.visual_override_confidence = visual_override_confidence

    def evaluate(self, detection: Detection) -> FusionResult:
        visual_probability = 0.65 * detection.confidence + 0.35 * detection.impact_score
        contributions: dict[str, float] = {
            "prior": -0.4,
            "visual": round(5.0 * (visual_probability - 0.55), 4),
        }
        evidence = [
            f"visual probability {visual_probability:.3f} from detector confidence and impact"
        ]
        if detection.stopped_vehicle:
            contributions["stopped_vehicle"] = 0.35
            evidence.append("persistent stopped-vehicle evidence increased risk")
        effective: dict[str, tuple[SensorReading, float]] = {}
        for reading in detection.sensor_readings:
            reading_reliability = effective_reliability(reading, self.freshness_half_life_ms)
            weight = self.SENSOR_WEIGHTS.get(reading.sensor_type, 2.0)
            contribution = weight * reading_reliability * (reading.probability - 0.5)
            contributions[reading.sensor_type] = round(contribution, 4)
            effective[reading.sensor_type] = (reading, reading_reliability)
            evidence.append(
                f"{reading.sensor_type} probability {reading.probability:.3f}, "
                f"effective reliability {reading_reliability:.3f}"
            )

        strong_sources = int(visual_probability >= 0.7) + sum(
            reading.probability >= 0.7 and reliability >= 0.5
            for reading, reliability in effective.values()
        )
        if strong_sources >= 2:
            contributions["agreement_bonus"] = 0.45
            evidence.append("independent evidence agreement bonus applied")

        reliable_auxiliary = [item for item in effective.values() if item[1] >= 0.65]
        if (
            visual_probability >= 0.7
            and len(reliable_auxiliary) >= 2
            and all(reading.probability <= 0.25 for reading, _ in reliable_auxiliary)
        ):
            contributions["contradiction_penalty"] = -0.9
            evidence.append("reliable smoke and audio evidence contradict the visual alert")

        log_odds = sum(contributions.values())
        probability = 1 / (1 + math.exp(-log_odds))
        override_candidates = [
            (reading.sensor_type, reading.probability)
            for reading, reliability in effective.values()
            if reading.probability >= self.override_probability
            and reliability >= self.override_reliability
        ]
        override_source = (
            max(override_candidates, key=lambda item: item[1])[0] if override_candidates else None
        )
        if (
            detection.impact_score >= self.visual_override_impact
            and detection.confidence >= self.visual_override_confidence
        ):
            override_source = "visual_impact"
            evidence.append(
                "guarded visual override activated: "
                f"impact {detection.impact_score:.3f} >= {self.visual_override_impact:.3f} and "
                f"confidence {detection.confidence:.3f} >= {self.visual_override_confidence:.3f}"
            )
        if override_source is not None:
            probability = max(probability, 0.9)
            if override_source != "visual_impact":
                evidence.append(f"guarded override activated by {override_source} sensor")

        probability = round(probability, 4)
        return FusionResult(
            probability=probability,
            verified=probability >= self.threshold or override_source is not None,
            threshold=self.threshold,
            override_source=override_source,
            contributions=contributions,
            evidence=tuple(evidence),
        )
