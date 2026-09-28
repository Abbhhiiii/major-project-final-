"""Build and validate portable video/synthetic-sensor demonstration pairs."""
from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import asdict
from pathlib import Path

from packages.surveillance.domain.models import Detection, SensorReading
from packages.surveillance.infrastructure.config import Settings
from packages.surveillance.perception.detectors import UltralyticsAccidentDetector
from packages.surveillance.perception.frame_reader import OpenCVFrameReader
from packages.surveillance.perception.sensor_candidates import SensorCandidateDetector
from packages.surveillance.verification import EvidenceFusionModel

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "demo_assets/test_videos"
OUTPUT = ROOT / "demo_assets/professor_demo"


def sensor(kind: str, probability: float, reliability: float = .95, age: int = 100) -> dict:
    return {"sensor_type": kind, "probability": probability, "reliability": reliability, "age_ms": age}


CASES = [
    ("01_all_sources_agree", "image2-accident-test.mp4", [sensor("smoke", .84), sensor("audio", .88)], "verified", None),
    ("02_smoke_only_override", "neutral-gray.mp4", [sensor("smoke", .97), sensor("audio", .1)], "verified", "smoke"),
    ("03_audio_only_override", "neutral-gray.mp4", [sensor("smoke", .1), sensor("audio", .98)], "verified", "audio"),
    ("04_borderline_visual_corroborated", "image7-accident-test.mp4", [sensor("smoke", .76), sensor("audio", .81)], "verified", None),
    ("05_visual_contradicted", "image2-accident-test.mp4", [sensor("smoke", .08), sensor("audio", .1)], "suppressed", None),
    ("06_stale_sensor_spike", "neutral-gray.mp4", [sensor("smoke", .99, .95, 60000), sensor("audio", .99, .95, 60000)], "no_candidate", None),
    ("07_unreliable_sensor_spike", "neutral-gray.mp4", [sensor("smoke", .99, .2), sensor("audio", .99, .2)], "no_candidate", None),
    ("08_missing_sensors_visual_only", "image2-accident-test.mp4", [], "verified", None),
    ("09_normal_scene", "neutral-gray.mp4", [sensor("smoke", .05), sensor("audio", .08)], "no_candidate", None),
    ("10_sensor_candidate_rejected", "neutral-gray.mp4", [sensor("smoke", .75), sensor("audio", .1)], "suppressed", None),
    ("11_borderline_visual_only", "image7-accident-test.mp4", [], "suppressed", None),
]


def main() -> None:
    settings = Settings()
    if settings.accident_model_path is None:
        raise SystemExit("Configure the accident model first")
    if settings.force_accept_verification:
        raise SystemExit("Disable forced verification acceptance before generating the demo")
    detector = UltralyticsAccidentDetector(settings.accident_model_path, settings.accident_confidence_threshold)
    reader = OpenCVFrameReader()
    candidate_detector = SensorCandidateDetector(settings.sensor_candidate_probability, settings.sensor_candidate_reliability)
    fusion = EvidenceFusionModel(settings.verification_threshold, settings.sensor_override_probability, settings.sensor_override_reliability)
    cache = {}
    for source_name in {case[1] for case in CASES}:
        _, frames = reader.frames(SOURCE / source_name, settings.frame_sample_fps)
        cache[source_name] = [output for frame in frames for output in detector.detect(frame, camera_id="DEMO-01", location="Professor demo zone")]

    OUTPUT.mkdir(exist_ok=True)
    catalog = {}
    results = []
    for name, source_name, sensors, expected, expected_override in CASES:
        filename = name + ".mp4"
        shutil.copy2(SOURCE / source_name, OUTPUT / filename)
        readings = tuple(SensorReading(**item, source="demo_metadata") for item in sensors)
        sources = candidate_detector.detect(readings)
        visual = cache[source_name]
        verification = None
        candidate = None
        if visual or sources:
            candidate = Detection(
                "DEMO-01", max((v.confidence for v in visual), default=0),
                max((v.vehicle_count for v in visual), default=0), False,
                max((v.impact_score for v in visual), default=0), "Professor demo zone",
                sensor_readings=readings, candidate_sources=(("visual",) if visual else ()) + sources,
            )
            verification = fusion.evaluate(candidate)
        actual = "no_candidate" if verification is None else "verified" if verification.verified else "suppressed"
        override = verification.override_source if verification else None
        if (actual, override) != (expected, expected_override):
            raise AssertionError(f"{name}: expected {(expected, expected_override)}, received {(actual, override)}")
        entry = {
            "scenario": name, "candidate_timestamp_ms": 1500, "sensors": sensors,
            "synthetic": True, "source_clip": source_name,
            "video_sha256": hashlib.sha256((OUTPUT / filename).read_bytes()).hexdigest(),
            "expected_outcome": expected, "expected_override": expected_override,
        }
        catalog[filename] = entry
        (OUTPUT / (name + ".json")).write_text(json.dumps({"schema_version": 1, "clips": {filename: entry}}, indent=2) + "\n")
        results.append({"video": filename, "outcome": actual, "candidate_sources": candidate.candidate_sources if candidate else [], "verification": asdict(verification) if verification else None})
    (OUTPUT / "sensor-metadata.json").write_text(json.dumps({"schema_version": 1, "clips": catalog}, indent=2) + "\n")
    # Register the exact same entries in the server's existing demo catalog.
    manifest = SOURCE / "sensor-metadata.json"
    payload = json.loads(manifest.read_text())
    payload["clips"].update(catalog)
    manifest.write_text(json.dumps(payload, indent=2) + "\n")
    (OUTPUT / "validation-results.json").write_text(json.dumps({
        "model_sha256": hashlib.sha256(settings.accident_model_path.read_bytes()).hexdigest(),
        "cv_threshold": settings.accident_confidence_threshold,
        "frame_sample_fps": settings.frame_sample_fps,
        "results": results,
    }, indent=2) + "\n")
    lines = ["# Sentrix professor demonstration", "", "Each numbered MP4 has a matching JSON file. Keep the filenames unchanged.",
        "Sensor readings are synthetic probability fixtures; the videos are reused short model-test clips, including still-image scenes and neutral backgrounds. Audio metadata is not extracted from an audio track. These are controlled software demonstrations, not sensor accuracy benchmarks.", "",
        "## Run", "", "1. Restart the backend after generating this pack: sensor metadata is read at startup.",
        "2. Open the dashboard, sign in, and upload your policy PDF.",
        "3. Upload one numbered MP4, enter a location, and click Scan uploaded footage.",
        "4. Inspect the candidate sources, verification evidence, and AI response. No-candidate cases produce no new decision.",
        "5. Keep Twilio/WhatsApp disabled while rehearsing. Groq needs a configured key. Its final severity and actions depend on the policy and contact configuration.", "",
        "The server automatically finds synthetic sensors by original filename in demo_assets/test_videos/sensor-metadata.json. The paired JSON files are for inspection; the UI does not upload them. The combined catalog here can also be selected via SURVEILLANCE_SENSOR_METADATA_PATH.", "",
        "## Verified results", "", "| Video | Candidate sources | Verification | Fused score | Override |", "|---|---|---|---|---|"]
    for item in results:
        result = item["verification"]
        lines.append(f"| {item['video']} | {', '.join(item['candidate_sources']) or 'none'} | {item['outcome']} | {result['probability'] if result else '—'} | {(result['override_source'] or 'none') if result else '—'} |")
    lines += ["", "Compare 04 and 11: identical footage with versus without sensor support. Compare 01, 05, and 08: identical footage with agreement, contradiction, or missing auxiliary data.", "",
        "Case 05 is a hypothetical contradiction test, not proof that the accident footage is a false alarm. Absence of smoke or audio does not generally rule out an incident; production coefficients need real-data calibration.", "",
        "validation-results.json records actual CV/fusion results, without calling Groq or external notification services. Rebuild with `.venv/bin/python -m scripts.build_professor_demo`."]
    (OUTPUT / "README.md").write_text("\n".join(lines) + "\n")
    print(f"Validated {len(results)} scenarios. Saved videos, paired JSON, guide and results to {OUTPUT}")


if __name__ == "__main__":
    main()
