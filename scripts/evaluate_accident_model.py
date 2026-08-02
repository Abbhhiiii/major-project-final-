from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from packages.surveillance.infrastructure.config import Settings
from packages.surveillance.perception.detectors import UltralyticsAccidentDetector
from packages.surveillance.perception.frame_reader import OpenCVFrameReader


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the accident model on labeled videos")
    parser.add_argument("manifest", type=Path, help="CSV with path,label columns")
    parser.add_argument("--threshold-sweep", action="store_true", help="Compare thresholds from 0.1 to 0.9")
    arguments = parser.parse_args()
    settings = Settings()
    if settings.accident_model_path is None:
        raise SystemExit("SURVEILLANCE_ACCIDENT_MODEL_PATH is required")
    inference_threshold = 0.01 if arguments.threshold_sweep else settings.accident_confidence_threshold
    detector = UltralyticsAccidentDetector(settings.accident_model_path, inference_threshold)
    reader = OpenCVFrameReader()
    samples: list[dict[str, object]] = []
    with arguments.manifest.open(newline="", encoding="utf-8") as source:
        for item in csv.DictReader(source):
            path = (arguments.manifest.parent / item["path"]).resolve()
            expected = item["label"].strip() == "1"
            _, frames = reader.frames(path, settings.frame_sample_fps)
            confidences = [
                output.confidence
                for frame in frames
                for output in detector.detect(frame, camera_id="evaluation", location="evaluation")
            ]
            samples.append({"path": str(path), "expected": expected, "max_confidence": round(max(confidences, default=0), 4)})
    result = evaluate(samples, settings.accident_confidence_threshold)
    if arguments.threshold_sweep:
        result["threshold_sweep"] = [evaluate(samples, value / 10, include_samples=False) for value in range(1, 10)]
    print(json.dumps(result, indent=2))


def evaluate(samples: list[dict[str, object]], threshold: float, include_samples: bool = True) -> dict[str, object]:
    totals = {"true_positive": 0, "true_negative": 0, "false_positive": 0, "false_negative": 0}
    results: list[dict[str, object]] = []
    for sample in samples:
        expected = bool(sample["expected"]); predicted = float(sample["max_confidence"]) >= threshold
        outcome = "true_positive" if expected and predicted else "false_negative" if expected else "false_positive" if predicted else "true_negative"
        totals[outcome] += 1; results.append({**sample, "predicted": predicted, "outcome": outcome})
    tp, fp, fn = totals["true_positive"], totals["false_positive"], totals["false_negative"]
    precision = tp / (tp + fp) if tp + fp else 0
    recall = tp / (tp + fn) if tp + fn else 0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0
    output: dict[str, object] = {"threshold": threshold, **totals, "precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4)}
    if include_samples: output["results"] = results
    return output


if __name__ == "__main__":
    main()
