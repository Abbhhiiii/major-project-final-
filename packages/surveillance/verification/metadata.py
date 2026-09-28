from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..domain.models import SensorReading


class SensorMetadataError(ValueError):
    """Raised when an uploaded synthetic sensor profile is unsafe or malformed."""


@dataclass(frozen=True)
class SensorMetadataProfile:
    scenario: str
    candidate_timestamp_ms: int
    sensors: tuple[SensorReading, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "scenario": self.scenario,
            "candidate_timestamp_ms": self.candidate_timestamp_ms,
            "sensors": [
                {
                    "sensor_type": item.sensor_type,
                    "probability": item.probability,
                    "reliability": item.reliability,
                    "age_ms": item.age_ms,
                }
                for item in self.sensors
            ],
        }


def parse_sensor_metadata(payload: object, source: str) -> SensorMetadataProfile:
    if not isinstance(payload, dict):
        raise SensorMetadataError("Sensor metadata must be a JSON object")
    allowed = {"schema_version", "scenario", "candidate_timestamp_ms", "sensors"}
    unknown = set(payload) - allowed
    if unknown:
        raise SensorMetadataError(f"Unknown sensor metadata fields: {', '.join(sorted(unknown))}")
    if payload.get("schema_version") != 1:
        raise SensorMetadataError("sensor metadata schema_version must be 1")
    scenario = payload.get("scenario")
    if not isinstance(scenario, str) or not scenario.strip() or len(scenario) > 250:
        raise SensorMetadataError("scenario must be a non-empty string of at most 250 characters")
    timestamp = payload.get("candidate_timestamp_ms", 0)
    if not isinstance(timestamp, int) or isinstance(timestamp, bool) or timestamp < 0:
        raise SensorMetadataError("candidate_timestamp_ms must be a non-negative integer")
    raw_sensors = payload.get("sensors")
    if not isinstance(raw_sensors, list) or not 1 <= len(raw_sensors) <= 10:
        raise SensorMetadataError("sensors must contain between 1 and 10 readings")
    readings: list[SensorReading] = []
    sensor_types: set[str] = set()
    for position, raw in enumerate(raw_sensors, start=1):
        if not isinstance(raw, dict):
            raise SensorMetadataError(f"sensor {position} must be a JSON object")
        if set(raw) != {"sensor_type", "probability", "reliability", "age_ms"}:
            raise SensorMetadataError(
                f"sensor {position} requires exactly sensor_type, probability, reliability, and age_ms"
            )
        sensor_type = raw.get("sensor_type")
        if not isinstance(sensor_type, str) or not sensor_type.strip() or len(sensor_type) > 50:
            raise SensorMetadataError(f"sensor {position} has an invalid sensor_type")
        normalized_type = sensor_type.strip().lower()
        if normalized_type in sensor_types:
            raise SensorMetadataError(f"duplicate sensor_type: {normalized_type}")
        sensor_types.add(normalized_type)
        probability = raw.get("probability")
        reliability = raw.get("reliability")
        age_ms = raw.get("age_ms")
        if not isinstance(probability, (int, float)) or isinstance(probability, bool):
            raise SensorMetadataError(f"sensor {position} probability must be numeric")
        if not isinstance(reliability, (int, float)) or isinstance(reliability, bool):
            raise SensorMetadataError(f"sensor {position} reliability must be numeric")
        if not isinstance(age_ms, int) or isinstance(age_ms, bool):
            raise SensorMetadataError(f"sensor {position} age_ms must be an integer")
        try:
            readings.append(
                SensorReading(
                    normalized_type,
                    float(probability),
                    float(reliability),
                    age_ms,
                    source,
                )
            )
        except ValueError as error:
            raise SensorMetadataError(f"sensor {position}: {error}") from error
    return SensorMetadataProfile(scenario.strip(), timestamp, tuple(readings))


class UploadedSensorMetadataStore:
    """Persists validated demo sensor profiles beside local video storage by video ID."""

    MAX_BYTES = 64 * 1024

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)

    def parse(self, content: bytes) -> SensorMetadataProfile:
        if not content:
            raise SensorMetadataError("Sensor metadata file is empty")
        if len(content) > self.MAX_BYTES:
            raise SensorMetadataError("Sensor metadata file exceeds 64 KB")
        try:
            payload = json.loads(content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise SensorMetadataError("Sensor metadata must be valid UTF-8 JSON") from error
        return parse_sensor_metadata(payload, "uploaded_metadata")

    def save(self, video_id: str, profile: SensorMetadataProfile) -> None:
        self._path(video_id).write_text(json.dumps(profile.as_dict(), indent=2), encoding="utf-8")

    def get(self, video_id: str) -> SensorMetadataProfile | None:
        path = self._path(video_id)
        if not path.is_file():
            return None
        try:
            return parse_sensor_metadata(
                json.loads(path.read_text(encoding="utf-8")), "uploaded_metadata"
            )
        except (OSError, json.JSONDecodeError, SensorMetadataError):
            return None

    def _path(self, video_id: str) -> Path:
        safe_id = Path(video_id).name
        if safe_id != video_id:
            raise SensorMetadataError("Invalid video ID")
        return self.directory / f"{safe_id}.json"


class MetadataSensorProvider:
    """Loads repeatable synthetic sensor readings keyed by original video filename."""

    def __init__(
        self, path: Path | None, uploaded: UploadedSensorMetadataStore | None = None
    ) -> None:
        self.path = path
        self.uploaded = uploaded
        self._clips: dict[str, object] = {}
        if path is not None and path.is_file():
            payload = json.loads(path.read_text(encoding="utf-8"))
            self._clips = dict(payload.get("clips", {}))

    def readings_for(self, filename: str, video_id: str | None = None) -> tuple[SensorReading, ...]:
        profile = self.uploaded.get(video_id) if self.uploaded is not None and video_id else None
        if profile is not None:
            return profile.sensors
        clip = self._clips.get(filename, {})
        if not isinstance(clip, dict):
            return ()
        readings = clip.get("sensors", [])
        if not isinstance(readings, list):
            return ()
        return tuple(SensorReading(**item, source="demo_metadata") for item in readings)

    def timestamp_for(self, filename: str, video_id: str | None = None) -> int:
        profile = self.uploaded.get(video_id) if self.uploaded is not None and video_id else None
        if profile is not None:
            return profile.candidate_timestamp_ms
        clip = self._clips.get(filename, {})
        if not isinstance(clip, dict):
            return 0
        return max(0, int(clip.get("candidate_timestamp_ms", 0)))
