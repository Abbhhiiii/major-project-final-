from __future__ import annotations

import hashlib
import json
import math
import random
from pathlib import Path
from typing import ClassVar

from ..domain.models import SensorFrameSample, SensorReading, structured


class SyntheticSensorStreamGenerator:
    """Creates a reproducible temporal sensor-twin stream unique to each uploaded video."""

    SCENARIOS: ClassVar[tuple[str, ...]] = (
        "both_high",
        "both_low",
        "smoke_high",
        "audio_high",
        "randomized",
    )

    def scenario_for(self, video_id: str, requested: str = "randomized") -> str:
        del video_id
        if requested not in self.SCENARIOS:
            raise ValueError(f"Unsupported synthetic sensor scenario: {requested}")
        return requested

    def sample(
        self,
        video_id: str,
        scenario: str,
        *,
        position: int,
        total_frames: int,
        frame_index: int,
        timestamp_ms: int,
    ) -> SensorFrameSample:
        progress = (position - 1) / max(total_frames - 1, 1)
        seed = int.from_bytes(
            hashlib.sha256(f"{video_id}:{frame_index}:{timestamp_ms}".encode()).digest()[:8],
            "big",
        )
        generator = random.Random(seed)
        smoke, audio = self._signals(scenario, progress, generator)
        reliability_base = 0.91 + 0.055 * math.sin(progress * math.pi)
        smoke_reliability = self._clip(reliability_base + generator.uniform(-0.025, 0.025))
        audio_reliability = self._clip(reliability_base + generator.uniform(-0.03, 0.03))
        return SensorFrameSample(
            frame_index=frame_index,
            timestamp_ms=timestamp_ms,
            readings=(
                SensorReading(
                    "smoke",
                    round(smoke, 4),
                    round(smoke_reliability, 4),
                    generator.randint(35, 190),
                    "synthetic_live",
                ),
                SensorReading(
                    "audio",
                    round(audio, 4),
                    round(audio_reliability, 4),
                    generator.randint(20, 150),
                    "synthetic_live",
                ),
            ),
        )

    def _signals(
        self, scenario: str, progress: float, generator: random.Random
    ) -> tuple[float, float]:
        wave = math.sin(progress * math.pi * 3)
        smoke_noise = generator.uniform(-0.035, 0.035)
        audio_noise = generator.uniform(-0.05, 0.05)
        if scenario == "both_high":
            smoke = 0.88 + 0.035 * wave + smoke_noise
            audio = 0.9 + 0.03 * math.sin(progress * math.pi * 4) + audio_noise * 0.5
        elif scenario == "both_low":
            smoke = 0.1 + 0.025 * wave + smoke_noise * 0.5
            audio = 0.12 + 0.03 * math.sin(progress * math.pi * 5) + audio_noise * 0.5
        elif scenario == "smoke_high":
            smoke = 0.9 + 0.03 * wave + smoke_noise * 0.5
            audio = 0.12 + 0.03 * math.sin(progress * math.pi * 5) + audio_noise * 0.5
        elif scenario == "audio_high":
            smoke = 0.1 + 0.025 * wave + smoke_noise * 0.5
            audio = 0.91 + 0.025 * math.sin(progress * math.pi * 4) + audio_noise * 0.5
        else:
            smoke = generator.uniform(0.05, 0.95)
            audio = generator.uniform(0.05, 0.95)
        return self._clip(smoke), self._clip(audio)

    @staticmethod
    def _clip(value: float) -> float:
        return max(0.01, min(0.99, value))


class SyntheticSensorStreamStore:
    """Persists generated frame streams for authenticated post-action download."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        video_id: str,
        original_filename: str,
        scenario: str,
        samples: tuple[SensorFrameSample, ...],
    ) -> Path:
        payload = {
            "schema_version": 2,
            "source": "synthetic_sensor_twin",
            "generation_model": "sentrix_temporal_sensor_twin_v1",
            "video_id": video_id,
            "original_filename": original_filename,
            "scenario": scenario,
            "frame_count": len(samples),
            "samples": [structured(sample) for sample in samples],
        }
        path = self.path_for(video_id)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    def path_for(self, video_id: str) -> Path:
        safe_id = Path(video_id).name
        if safe_id != video_id:
            raise ValueError("Invalid video ID")
        return self.directory / f"{safe_id}.json"
