# Multimodal statistical verification model

Sentrix begins with multimodal candidate generation: visual CV, smoke, and audio can each nominate
an event for verification. It then combines all available evidence. The implementation is deterministic and provider-independent. Demo sensor readings are
synthetic; production deployments must replace them with synchronized sensor adapters and calibrate
the coefficients on labeled field data.

## Candidate generation

Each source independently evaluates whether an event deserves verification:

- A YOLO detection above its configured confidence threshold creates a `visual` candidate.
- Smoke or audio probability at or above `0.70`, with effective reliability at or above `0.50`,
  creates a sensor candidate.
- If several sources nominate the same clip, they are represented as one multimodal candidate.
- If YOLO finds nothing but a sensor nominates an event, Sentrix creates a sensor-only candidate with
  visual confidence and impact set to zero rather than inventing visual evidence.
- Weak, stale, or unreliable sensor readings cannot create a candidate.

Candidate generation is deliberately permissive; verification makes the final statistical decision.

## Inputs

- Visual probability: `0.65 × detector confidence + 0.35 × visual impact score`
- Smoke probability: normalized to `[0, 1]`
- Audio anomaly probability: normalized to `[0, 1]`
- Reliability: per-reading quality estimate in `[0, 1]`
- Age: milliseconds between the reading and the candidate event

Missing auxiliary readings contribute zero evidence. They are not interpreted as proof that an
incident did not occur.

## Freshness and effective reliability

Sensor reliability decays with a 10-second half-life:

```text
freshness = exp(-ln(2) × age_ms / 10000)
effective_reliability = reliability × freshness
```

This prevents old or low-quality readings from dominating a current event.

## Logistic evidence fusion

The model accumulates evidence in log-odds space:

```text
z = -0.40
  + 5.00 × (visual_probability - 0.55)
  + 3.20 × effective_smoke_reliability × (smoke_probability - 0.50)
  + 2.80 × effective_audio_reliability × (audio_probability - 0.50)
  + contextual adjustments

fused_probability = 1 / (1 + exp(-z))
```

Contextual adjustments include `+0.35` for persistent stopped-vehicle evidence and `+0.45` when
at least two independent sources are strong. When visual probability is high but two reliable
auxiliary sensors are both at or below `0.25`, a `-0.90` contradiction penalty reduces visual false
alarms.

The default verification threshold is `0.68`.

## Persistent bounded adaptive threshold

The factory default is `0.68`. Sentrix persists a learned baseline for each organization/location
and may make a small adjustment from up to five
comparable, human-reviewed incidents retrieved for the same location and sensor profile. Raw sensor
values are not reused in this adjustment: they already influence the fused probability, so using
them again would double-count evidence.

For reviewed incident `i`:

```text
recency_i = 2 ^ (-age_days_i / 90)
weight_i = similarity_i × recency_i
direction_i = +1 for a prior false alarm or overestimate
              -1 for a prior underestimate
               0 for a confirmed/correct or conflicting review

adjustment = 0.08 × Σ(new_weight_i × direction_i) / (3 + Σ new_weight_i)
final_threshold = clip(learned_baseline + adjustment, 0.60, 0.76)
```

A false alarm raises the threshold slightly; a previously underestimated incident lowers it.
Correct reviews still count in the denominator, stabilizing the model without pushing it in either
direction. Each review version (`incident_id@reviewed_at`) is incorporated once. The final threshold
is persisted as the next scan's learned baseline; retrieving the same review again reuses that
baseline without another movement. The stabilizer of `3` prevents one review from causing a large jump, the 90-day half-life
reduces stale influence, and the hard bounds prevent dangerous threshold drift. The audit stores the
baseline, final threshold, adjustment, baseline outcome, adaptive outcome, and every contributing
review so the analytics page can reconstruct the change exactly.

The guarded evidence overrides remain independent of this threshold. A configured demo force-accept
gate can change the pipeline outcome, but cannot overwrite the recorded baseline or adaptive result.

## Guarded override

An auxiliary sensor can override a weak combined score only when both conditions hold:

- Probability is at least `0.92`
- Effective reliability is at least `0.80`

The override sets a minimum fused probability of `0.90` and records the responsible sensor. This
supports cases such as dense smoke with weak or obstructed video while preventing an unreliable or
stale sensor spike from taking control.

A visual candidate can independently override when visual impact is at least `0.90` and detector
confidence is at least `0.75`. Requiring both makes the override resistant to a single noisy visual
metric. It records `visual_impact` as its source and applies the same minimum fused probability of
`0.90`, even when reliable low smoke/audio values caused a low pre-override logistic score.

## Agent decision contract

Groq receives three explicit JSON objects:

1. `scanning_layer`: candidate sources, CV confidence, impact, location, timestamp, and raw sensor readings.
2. `verification_layer`: fused probability, threshold, per-source contributions, evidence, and any
   override.
3. `policy_retrieval`: retrieved policy excerpts, contacts, procedures, preferences, and prior
   incident context.

The reasoning prompt requires the decision to reconcile all three sources, cite the evidence and
policy that drove the result, treat missing sensors as unknown, and never invent observations.

## Per-frame synthetic sensor twin

For demo footage, Sentrix generates one smoke reading and one audio reading for every decoded frame.
The operator explicitly selects both-high, both-low, smoke-high, audio-high, or randomized. Each
mode adds bounded seeded per-frame noise and quality variation. Generation is deterministic for the
same video/frame/timestamp and selection, allowing repeatable comparisons in Decision Reconstruction.

The reading nearest the selected CV candidate enters fusion. Sensors can also nominate a candidate
at their own strongest frame when the visual model finds nothing. The complete timeline is retained
losslessly in the audit and analytics. Reasoning receives a bounded temporal summary covering every
frame (including count, duration, minimum, maximum, mean, variability, reliability, threshold
crossings, and the peak frame/time), while reviewed-memory matching compares timeline mean, maximum,
and variability in addition to candidate-frame values. Every generated reading is tagged
`synthetic_live`, so it cannot be mistaken for physical sensor evidence.

After planning and execution finish, the complete versioned stream is available as a JSON download
from the Operations page. Decision Reconstruction plots every probability and effective-reliability
reading and marks the exact incident frame used for fusion.

## Production calibration

The current coefficients are transparent expert-initialized priors, not learned claims. Production
calibration requires synchronized, independently labeled visual/smoke/audio events. Fit coefficients
on a training partition, select the operating threshold from precision-recall and expected-cost
analysis, then report calibration error, Brier score, sensitivity, specificity, precision, recall,
F1, false-alarm rate per camera-hour, and performance under missing-sensor patterns on a held-out
test partition.
