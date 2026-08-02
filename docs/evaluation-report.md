# Accident model evaluation report

## Scope

This is a functional regression set, not a general accuracy benchmark. It contains seven accident clips derived from the model repository's sample images and three synthetic neutral clips. A defensible accuracy claim requires independently collected real accident and non-accident footage.

## Current threshold (`0.5`)

- True positives: 4
- True negatives: 3
- False positives: 0
- False negatives: 3
- Precision: 1.0000
- Recall: 0.5714
- F1: 0.7273

False negatives are clips 3, 4, and 6. Their maximum decoded-video confidences are `0.2007`, `0.0530`, and `0.0000` respectively.

## Threshold investigation

Thresholds `0.1` and `0.2` recover clip 3 and raise functional-set recall to `0.7143` and F1 to `0.8333`, without false positives among the three synthetic neutral clips. The production threshold remains `0.5` because the negative set is too weak to justify lowering it safely. The correct next model step is validation on diverse real non-accident traffic footage, followed by threshold selection or retraining.

## Reproduce

```bash
.venv/bin/python -m scripts.evaluate_accident_model demo_assets/test_videos/evaluation-manifest.csv --threshold-sweep
```
