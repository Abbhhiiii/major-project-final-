# Accident model test clips

These three-second MP4 clips are encoded from the accident-model repository's sample images. Results below were measured from the decoded MP4 frames with `best.pt` and the configured `0.5` confidence threshold.

| Clip | Expected detections | Measured confidence |
| --- | ---: | ---: |
| `image1-accident-test.mp4` | 1 | 0.710 |
| `image2-accident-test.mp4` | 1 | 0.897 |
| `image3-accident-test.mp4` | 0 | below 0.5 |
| `image4-accident-test.mp4` | 0 | below 0.5 |
| `image5-accident-test.mp4` | 1 | 0.587 |
| `image6-accident-test.mp4` | 0 | below 0.5 |
| `image7-accident-test.mp4` | 1 | 0.543 |

Use clips 1, 2, 5, and 7 as positive pipeline checks. Clips 3, 4, and 6 are useful false-negative/model-recall checks: they contain repository sample scenes but do not pass the current threshold after MP4 encoding. Each clip has neutral lead-in frames and one sampled accident frame to avoid duplicate incidents. These clips are a functional test set, not a statistically valid accuracy benchmark.

Run the repeatable evaluation with:

```bash
.venv/bin/python -m scripts.evaluate_accident_model demo_assets/test_videos/evaluation-manifest.csv
```

On this small functional set at threshold `0.5`, the measured results are precision `1.0000`, recall `0.5714`, and F1 `0.7273` (4 true positives, 3 true negatives, 0 false positives, and 3 false negatives). Do not present these figures as general model accuracy; a larger independently labeled video dataset is required for that claim.
