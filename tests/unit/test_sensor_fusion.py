from pathlib import Path

import pytest

from packages.surveillance.domain.models import Detection, SensorReading
from packages.surveillance.perception.sensor_candidates import SensorCandidateDetector
from packages.surveillance.perception.synthetic_sensors import SyntheticSensorStreamGenerator
from packages.surveillance.verification import (
    EvidenceFusionModel,
    MetadataSensorProvider,
    UploadedSensorMetadataStore,
)


def detection(*readings: SensorReading, confidence: float = 0.72, impact: float = 0.7) -> Detection:
    return Detection("cam-1", confidence, 1, False, impact, "North Gate", sensor_readings=readings)


def test_independent_sensor_agreement_increases_probability() -> None:
    model = EvidenceFusionModel()
    visual_only = model.evaluate(detection())
    corroborated = model.evaluate(
        detection(
            SensorReading("smoke", 0.82, 0.9, 100),
            SensorReading("audio", 0.86, 0.9, 100),
        )
    )
    assert corroborated.probability > visual_only.probability
    assert corroborated.verified is True
    assert "agreement_bonus" in corroborated.contributions


def test_reliable_auxiliary_contradiction_suppresses_visual_false_alarm() -> None:
    result = EvidenceFusionModel().evaluate(
        detection(
            SensorReading("smoke", 0.08, 0.95, 100),
            SensorReading("audio", 0.10, 0.94, 100),
            confidence=0.9,
            impact=0.85,
        )
    )
    assert result.verified is False
    assert result.contributions["contradiction_penalty"] < 0


def test_extreme_visual_impact_overrides_low_fused_sensor_score() -> None:
    result = EvidenceFusionModel().evaluate(
        detection(
            SensorReading("smoke", 0.08, 0.95, 100),
            SensorReading("audio", 0.10, 0.94, 100),
            confidence=0.8,
            impact=0.95,
        )
    )

    assert result.verified is True
    assert result.probability == 0.9
    assert result.override_source == "visual_impact"
    assert any("guarded visual override" in item for item in result.evidence)


def test_exceptionally_strong_reliable_sensor_can_override_combined_score() -> None:
    result = EvidenceFusionModel().evaluate(
        detection(
            SensorReading("smoke", 0.97, 0.92, 100),
            confidence=0.25,
            impact=0.3,
        )
    )
    assert result.verified is True
    assert result.probability == 0.9
    assert result.override_source == "smoke"


def test_stale_unreliable_sensor_has_limited_influence() -> None:
    model = EvidenceFusionModel()
    baseline = model.evaluate(detection()).probability
    stale = model.evaluate(detection(SensorReading("audio", 0.99, 0.2, 60_000))).probability
    assert stale - baseline < 0.02


def test_demo_metadata_is_repeatable_and_marks_its_source() -> None:
    provider = MetadataSensorProvider(Path("demo_assets/test_videos/sensor-metadata.json"))
    first = provider.readings_for("image2-accident-test.mp4")
    second = provider.readings_for("image2-accident-test.mp4")
    assert first == second
    assert {item.sensor_type for item in first} == {"smoke", "audio"}
    assert all(item.source == "demo_metadata" for item in first)


def test_initial_scan_allows_fresh_reliable_sensor_candidate() -> None:
    detector = SensorCandidateDetector()
    sources = detector.detect(
        (
            SensorReading("smoke", 0.95, 0.9, 100),
            SensorReading("audio", 0.99, 0.2, 60_000),
        )
    )
    assert sources == ("smoke",)


def test_synthetic_stream_generates_one_reproducible_reading_pair_per_frame() -> None:
    generator = SyntheticSensorStreamGenerator()
    scenario = generator.scenario_for("video-123")
    first = generator.sample(
        "video-123",
        scenario,
        position=4,
        total_frames=30,
        frame_index=3,
        timestamp_ms=1500,
    )
    second = generator.sample(
        "video-123",
        scenario,
        position=4,
        total_frames=30,
        frame_index=3,
        timestamp_ms=1500,
    )

    assert first == second
    assert {reading.sensor_type for reading in first.readings} == {"smoke", "audio"}
    assert {reading.source for reading in first.readings} == {"synthetic_live"}


def test_different_videos_receive_different_seeded_streams() -> None:
    generator = SyntheticSensorStreamGenerator()
    first = generator.sample(
        "video-a",
        generator.scenario_for("video-a"),
        position=8,
        total_frames=30,
        frame_index=7,
        timestamp_ms=3500,
    )
    second = generator.sample(
        "video-b",
        generator.scenario_for("video-b"),
        position=8,
        total_frames=30,
        frame_index=7,
        timestamp_ms=3500,
    )

    assert first != second


@pytest.mark.parametrize(
    ("scenario", "smoke_range", "audio_range"),
    [
        ("both_high", (0.8, 0.99), (0.8, 0.99)),
        ("both_low", (0.01, 0.2), (0.01, 0.2)),
        ("smoke_high", (0.8, 0.99), (0.01, 0.2)),
        ("audio_high", (0.01, 0.2), (0.8, 0.99)),
    ],
)
def test_operator_sensor_scenarios_have_expected_signal_ranges(
    scenario: str,
    smoke_range: tuple[float, float],
    audio_range: tuple[float, float],
) -> None:
    sample = SyntheticSensorStreamGenerator().sample(
        "video-test",
        scenario,
        position=15,
        total_frames=30,
        frame_index=14,
        timestamp_ms=7000,
    )
    readings = {item.sensor_type: item.probability for item in sample.readings}

    assert smoke_range[0] <= readings["smoke"] <= smoke_range[1]
    assert audio_range[0] <= readings["audio"] <= audio_range[1]


def test_randomized_sensor_scenario_is_repeatable_per_frame() -> None:
    generator = SyntheticSensorStreamGenerator()
    first = generator.sample(
        "video-random",
        "randomized",
        position=8,
        total_frames=30,
        frame_index=7,
        timestamp_ms=3500,
    )
    second = generator.sample(
        "video-random",
        "randomized",
        position=8,
        total_frames=30,
        frame_index=7,
        timestamp_ms=3500,
    )

    assert first == second


@pytest.mark.parametrize(
    "filename",
    [
        "01_high_smoke_and_audio.json",
        "02_very_high_smoke_override.json",
        "03_very_high_audio_override.json",
        "04_low_smoke_and_audio.json",
        "05_stale_high_signals_no_override.json",
    ],
)
def test_per_footage_demo_sensor_profiles_are_valid(tmp_path: Path, filename: str) -> None:
    store = UploadedSensorMetadataStore(tmp_path / "metadata")
    profile = store.parse((Path("demo_assets/sensor_metadata_cases") / filename).read_bytes())

    assert {reading.sensor_type for reading in profile.sensors} == {"smoke", "audio"}
    assert all(reading.source == "uploaded_metadata" for reading in profile.sensors)
