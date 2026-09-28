# Sentrix: Complete Project Context for Report Generation

## 1. Document purpose

This document is a self-contained technical description of the Sentrix project. It is designed to
be uploaded to another large language model as the factual source for producing a final-year project
report, thesis chapter, presentation, viva preparation, or architecture explanation.

The document describes the implemented system rather than an aspirational design. It deliberately
does not include passwords, API keys, Twilio credentials, Groq credentials, authentication tokens,
or other secrets.

## 2. Project identity and objective

**Project name:** Sentrix

**Project category:** Context-aware and risk-aware AI surveillance framework

**Primary demonstration domain:** Road-incident and accident detection from uploaded CCTV footage

Sentrix converts uploaded surveillance footage into an auditable decision pipeline. It combines a
real computer-vision detector with synchronized auxiliary sensor evidence, statistical verification,
retrieval-augmented generation, an LLM decision agent, action planning, delivery/report execution,
and persistent human-reviewed memory.

The system is not only an accident classifier. Its main research idea is that a visual detection
should not directly trigger an emergency escalation. The detection must be checked against temporal
sensor evidence, relevant organizational policy, contact and procedure data, and previous reviewed
incidents before an agent selects an action.

## 3. Implemented end-to-end pipeline

```text
Video upload
  -> frame decoding and simulated live playback
  -> per-frame synthetic smoke/audio sensor twin
  -> sampled YOLO accident inference
  -> multimodal candidate generation
  -> temporal CV clustering
  -> reliability-aware statistical verification
  -> bounded adaptive threshold from reviewed memory
  -> policy RAG and similar-incident retrieval
  -> Groq structured reasoning
  -> action planning
  -> execution: dashboard + PDF + optional Twilio
  -> incident and audit memory
  -> human review
  -> reviewed intelligence available to future incidents
```

The seven agent-facing stages shown in the dashboard are:

1. Detection
2. Verification
3. Context retrieval
4. Reasoning
5. Planning
6. Execution
7. Memory

## 4. Architectural principles

The code follows a layered, ports-and-adapters-style architecture.

- **Presentation layer:** React dashboard, authentication/onboarding flow, live pipeline, policies,
  history, and decision reconstruction.
- **HTTP boundary:** FastAPI request validation, authentication requirements, REST endpoints, and
  Server-Sent Events.
- **Application layer:** video ingestion, video processing, orchestration, and use-case coordination.
- **Agent layer:** verification, retrieval, reasoning, planning, execution, memory, and audit agents.
- **Domain layer:** immutable typed dataclasses for detections, readings, decisions, plans, actions,
  events, incidents, and audits.
- **Perception layer:** OpenCV decoding, YOLO adapter, normalization, candidate generation, temporal
  clustering, and the synthetic sensor twin.
- **Knowledge layer:** PDF extraction, chunking, deterministic local embeddings, and ranked retrieval.
- **Verification layer:** logistic evidence fusion, guarded override, and adaptive decision boundary.
- **Memory layer:** persistent incidents, full audits, operator reviews, and similarity retrieval.
- **Execution/infrastructure layer:** SQLite/SQLAlchemy, Alembic, Groq, Twilio, PDF reports, logging,
  local file storage, and configuration.

Domain code does not depend directly on FastAPI, SQLAlchemy, Twilio, Groq, or Ultralytics SDK types.
External providers are translated through adapters and typed contracts.

## 5. Technology stack

### Backend and AI

- Python 3.11 or newer
- FastAPI for HTTP APIs and SSE endpoints
- Pydantic and pydantic-settings for validation and environment configuration
- SQLAlchemy 2 for persistence
- Alembic for versioned database migrations
- SQLite for the local demo database
- Ultralytics YOLO for real accident-model inference
- OpenCV for complete frame decoding and video timing
- Groq Python SDK for model-backed structured reasoning
- pypdf for PDF text extraction
- ReportLab for incident PDF generation
- Twilio Python SDK for voice calls and WhatsApp delivery
- httpx plus a cached/rate-limited Nominatim adapter for map geocoding

### Dashboard

- React 19
- TypeScript 5.9
- Vite 8
- Tailwind CSS 4 plus project-specific CSS/SVG visualizations
- Leaflet with OpenStreetMap tiles for camera location search and pin selection
- Browser Fetch API and ReadableStream for REST and SSE consumption

### Testing and quality

- pytest for unit and integration tests
- FastAPI TestClient/httpx for API-boundary testing
- Ruff for Python formatting and linting
- Vitest for frontend unit/component tests
- React Testing Library and jsdom
- ESLint for TypeScript/React linting
- TypeScript compiler and Vite production build as release checks

## 6. Main repository structure

```text
apps/backend/main.py
    FastAPI app construction, routes, dependency wiring, SSE, and integration status

apps/dashboard/src/
    React dashboard, API client, state hook, operations view, policies, history, and analytics

packages/surveillance/domain/
    Provider-independent domain entities and structured JSON conversion

packages/surveillance/application/
    Authentication helpers, upload use case, and video-processing workflow

packages/surveillance/perception/
    OpenCV frames, YOLO detector, normalization, candidates, and synthetic sensors

packages/surveillance/verification/
    Evidence fusion, adaptive threshold, and legacy metadata parser fixtures

packages/surveillance/knowledge/
    PDF ingestion and local feature-hash embeddings

packages/surveillance/data/
    SQLAlchemy models, repositories, onboarding/RAG repository, and reviewed memory

packages/surveillance/infrastructure/
    Settings, Groq reasoning, Twilio/PDF execution, local video storage, and event buffering

migrations/versions/
    Alembic schema history through migration 0012

tests/
    Domain, agent, model, delivery, and API integration tests
```

## 7. Video ingestion and frame processing

Uploaded videos are validated and stored locally. The supported dashboard upload formats are MP4,
MOV, AVI, and WebM. The default maximum size is 250 MB and is configurable.

OpenCV decodes every source frame. Each decoded frame contains:

- original source-frame index;
- timestamp in milliseconds;
- image matrix;
- a Boolean indicating whether YOLO should analyze that frame.

This separation is important. Sensor readings are generated for every decoded frame, while visual
inference uses the configured sampling rate, which defaults to 2 frames per second. Therefore, a
30-frame video creates exactly 30 synchronized sensor samples without requiring 30 expensive YOLO
predictions.

The video is paced as a simulated live feed. If `playback_speed = 4`, the delay between source
timestamps is divided by four. A value of zero disables pacing for tests.

## 8. Computer-vision model

The configured detector is an Ultralytics YOLO checkpoint stored outside the repository. The model
path is supplied through `SURVEILLANCE_ACCIDENT_MODEL_PATH`. Model weights are excluded from Git.

YOLO receives real decoded frames. Every bounding-box output is normalized into a provider-neutral
`DetectorOutput` containing:

- confidence;
- impact score;
- vehicle count;
- stopped-vehicle flag;
- frame timestamp;
- location.

The current adapter maps the trained class ID to an expert-defined impact value:

```text
impact_score = 0.70 when class_id = 0
impact_score = 0.95 otherwise
```

This is an explicit adapter rule, not a learned physical-impact measurement. The configured YOLO
confidence gate defaults to 0.50.

When no model path is configured, the application uses an unconfigured detector that raises a clear
error rather than fabricating detections.

## 9. Temporal clustering

Visual detections close in time are grouped so repeated boxes from the same event do not create many
incidents. The default maximum gap is five seconds.

For a cluster, Sentrix selects and aggregates:

```text
confidence      = maximum confidence in cluster
impact_score    = maximum impact score in cluster
vehicle_count   = maximum vehicle count in cluster
stopped_vehicle = true if any cluster detection is stopped
identity/time   = strongest detection by confidence, then impact
```

## 10. Per-frame synthetic sensor twin

The current demo does not claim access to physical smoke or microphone sensors. Instead, a local
sensor-twin generator creates explicitly labeled synthetic readings for every decoded video frame.
Each sample contains smoke and audio probability, reliability, reading age, frame index, and video
timestamp. Every reading has `source = synthetic_live`.

### 10.1 Reproducibility and variation

A SHA-256-derived seed uses video ID, frame index, and timestamp. Reprocessing the same stored video
with the same selected scenario produces the same stream. A different upload or scenario produces a
different stream. The API validates and stores the operator's selection on the processing job, and a
retry preserves it.

### 10.2 Available temporal scenarios

1. `both_high`
2. `both_low`
3. `smoke_high`
4. `audio_high`
5. `randomized`

### 10.3 Generator equations

Let normalized video progress be:

```text
p = (frame_position - 1) / max(total_frames - 1, 1)
clip(x) = min(0.99, max(0.01, x))
```

Small seeded noise and oscillation prevent perfectly flat artificial curves. High channels are
centered around 0.88–0.91, and low channels around 0.10–0.12. `randomized` draws each channel from
0.05–0.95 independently for every frame using the reproducible per-frame seed.

Raw reliability is approximately 0.91 to 0.965 with small seeded variation. Reading ages are also
seeded: smoke is approximately 35–190 ms old and audio approximately 20–150 ms old.

### 10.4 Live and post-action behavior

During processing, every frame's smoke and audio readings are emitted through the transient SSE
channel and accumulated in the Operations dashboard. After the scan, the dashboard reveals and
smoothly focuses each real pipeline result in order: verification mathematics, policy and reviewed
incident retrieval, Groq reasoning, planning, execution, and memory. A short presentation delay keeps
the stages readable without altering their values. The complete stream is stored as versioned JSON
and the same dashboard area exposes **Download generated JSON** after execution.

The downloadable schema includes:

```text
schema_version
source
generation_model
video_id
original_filename
scenario
frame_count
samples[]
```

## 11. Multimodal candidate generation

Candidate generation is deliberately permissive. Verification is responsible for suppression.

A visual candidate exists when YOLO returns an accepted detection. A sensor reading independently
nominates a candidate when:

```text
sensor_probability >= 0.70
effective_reliability >= 0.50
```

For a visual event, Sentrix selects the synthetic sensor frame nearest the CV timestamp. If YOLO
finds nothing but a sensor crosses its candidate gate, the strongest sensor frame becomes a
sensor-only candidate. Its visual confidence and impact are set to zero; visual evidence is never
invented.

The complete sensor timeline is attached to the detection audit, while the timestamp-nearest readings
are the ones used by statistical fusion.

## 12. Statistical verification model

### 12.1 Visual probability

```text
P_visual = 0.65 × detector_confidence + 0.35 × impact_score
```

Confidence receives greater weight because it is the detector's direct certainty. Impact provides
additional scene-severity information.

### 12.2 Sensor freshness

Sensor reliability decays exponentially with a ten-second half-life:

```text
freshness = exp(-ln(2) × age_ms / 10000)
effective_reliability = raw_reliability × freshness
```

At age zero, freshness is 1. At 10,000 ms, freshness is 0.5. Missing sensors contribute no term and
are treated as unknown rather than negative evidence.

### 12.3 Logistic evidence fusion

Evidence is accumulated in log-odds space:

```text
z = -0.40
  + 5.00 × (P_visual - 0.55)
  + 3.20 × effective_smoke_reliability × (P_smoke - 0.50)
  + 2.80 × effective_audio_reliability × (P_audio - 0.50)
  + contextual adjustments

P_fused = sigmoid(z) = 1 / (1 + exp(-z))
```

Interpretation:

- `-0.40` is the prior bias against declaring an incident without evidence.
- A modality probability above 0.50 adds positive evidence.
- A probability below 0.50 subtracts evidence in proportion to reliability.
- Smoke has coefficient 3.20 and audio 2.80.
- Visual evidence has coefficient 5.00 around the neutral point 0.55.

### 12.4 Contextual adjustments

```text
stopped-vehicle evidence: +0.35
agreement of at least two strong independent sources: +0.45
reliable visual-versus-sensor contradiction: -0.90
```

The contradiction penalty applies when visual probability is at least 0.70, both auxiliary sensors
have effective reliability at least 0.65, and both sensor probabilities are at most 0.25.

### 12.5 Guarded override

A single auxiliary sensor may override a weak combined score only when:

```text
sensor_probability >= 0.92
effective_reliability >= 0.80
```

The override sets a minimum fused probability of 0.90 and records the responsible sensor. This
supports smoke-obscured or visually weak incidents while preventing stale/unreliable spikes from
taking control.

Extreme visual evidence has a separate guarded path:

```text
visual_impact >= 0.90
detector_confidence >= 0.75
```

Both conditions are required. This allows an unmistakable high-impact visual candidate to survive
contradictory or low auxiliary readings, but prevents an uncertain detector or impact alone from
taking control. It also applies the 0.90 probability floor and records `visual_impact` as the
override source.

## 13. Persistent bounded adaptive verification threshold

The factory threshold is 0.68. Each organization/location has a persisted learned baseline, initially
0.68. Human-reviewed similar incidents can move it slightly, but the system prevents uncontrolled
learning, repeated application of the same review, or dangerous drift.

For reviewed incident `i`:

```text
recency_i = 2^(-age_days_i / 90)
weight_i = similarity_i × recency_i
```

Direction is:

```text
d_i = +1 for a prior false alarm or overestimated severity/action
d_i = -1 for a prior underestimated severity/action
d_i =  0 for a correct review or a conflicting correction
```

The threshold adjustment is:

```text
delta = 0.08 × Σ(new_weight_i × d_i) / (3 + Σ new_weight_i)
T_final = clip(T_learned_baseline + delta, 0.60, 0.76)
```

Every review is versioned as `incident_id@reviewed_at`. Only versions not already incorporated in
the location profile enter `new_weight`. After evaluation, `T_final` is persisted and becomes the
next scan's `T_learned_baseline`. Replaying the same clip or retrieving the same unchanged review
therefore reuses the learned threshold without applying the delta again. Editing a review creates a
new version that can contribute once.

Safety properties:

- maximum conceptual adjustment is eight percentage points;
- hard threshold bounds are 0.60 and 0.76;
- stabilizer 3 prevents one review from causing a large movement;
- a 90-day half-life reduces old influence;
- correct reviews count in the denominator and stabilize the model;
- conflicting severity/action corrections have zero direction;
- only up to five already-filtered comparable reviews are used;
- every immutable review version changes a location baseline at most once;
- the resulting threshold is stored per organization/location and reused by later scans;
- sensor values remain in fusion and are not counted again in threshold adaptation;
- guarded override is independent;
- forced demo acceptance cannot overwrite the recorded baseline/adaptive mathematical outcomes.

Decision Reconstruction shows the baseline, final boundary, adjustment, safety window, fused value,
baseline outcome, adaptive outcome, and each review's similarity, recency, weight, direction, and
signed pressure.

## 14. Human-reviewed incident memory

The original AI audit is immutable. A human review is stored separately and contains corrected
severity, corrected action, false-alarm status, reviewer reason, reviewer identity, and timestamp.

Retrieval is organization-scoped and location-scoped. Different tenants and locations cannot
influence one another. Sensor types must match; a missing sensor is not treated as a measured zero.
All qualifying reviews are scored and sorted, but only the single highest-similarity review is
returned to threshold adaptation, Groq, and decision reconciliation. Its influence cannot be diluted
or contradicted by a weaker match.

### 14.2 Similarity-weighted decision reconciliation

After Groq creates its current-evidence draft, the closest human-reviewed case is applied with an
explicit complementary weighting. Severity ranks are `low=0`, `medium=1`, `high=2`, `critical=3`;
action ranks are `none=0`, `message=1`, `call=2`.

```text
review_weight = similarity
current_weight = 1 - similarity
blended_rank = round_half_up(current_weight × Groq_draft_rank
                             + review_weight × human_reviewed_rank)
upward_review_floor = floor(similarity × human_reviewed_severity_rank)
final_severity_rank = max(blended_rank, upward_review_floor) for upward corrections
```

Therefore a 100% match has zero current-draft weight and reproduces the reviewed severity/action
exactly. A lower match influences the result proportionally instead of acting as a binary rule. A
reviewed `HIGH` at the retrieval floor cannot collapse below the similarity-derived severity floor;
at about 80% similarity its floor is at least `MEDIUM`. A review marked false alarm targets
`low/none`. This decision reconciliation runs only after the
candidate passes verification; it cannot make an unverified candidate notify somebody. The audit
stores both weights, both source outcomes, continuous rank scores, final outcome, incident ID, and
method version for complete reconstruction.

### 14.1 Per-feature similarity

For each numeric feature:

```text
match = max(0, 1 - min(1, abs(current - previous) / scale))
weighted_match = match × feature_weight
similarity = Σ weighted_match
```

With auxiliary sensors present, 30% of total weight belongs to visual evidence:

```text
CV confidence weight = 0.15
visual impact weight = 0.15
```

The remaining 70% is divided equally among sensor types. Within each sensor's share, the dimensions
are:

```text
candidate probability = 0.35
candidate reliability = 0.20
candidate freshness    = 0.10
timeline mean          = 0.15
timeline maximum       = 0.15
timeline variability   = 0.05
```

If an older audit has no timeline, the fallback sensor dimensions are candidate probability 0.50,
reliability 0.30, and freshness 0.20.

Freshness difference is normalized by a scale of 10,000 ms. Timeline variability uses a scale of
0.5. Other normalized probabilities use a scale of 1.0.

Only matches with similarity at least 0.70 are retrieved. Up to five are returned, sorted by
similarity and review time. The detailed feature matches appear in analytics and are also available
to Groq as bounded historical evidence.

## 15. Policy RAG system

### 15.1 Ingestion

Authenticated organizations upload PDF policies. `pypdf` extracts text from every page. Text is
tokenized on non-whitespace and chunked into groups of approximately 180 words. Empty/image-only PDFs
without extractable text are rejected.

### 15.2 Local feature-hash embedding

Sentrix uses a deterministic 256-dimensional local embedding for demo reliability and offline use.
For each lowercase alphanumeric token:

1. Compute a BLAKE2b digest.
2. Map the digest to `index mod 256`.
3. Add 1 to that vector position.
4. L2-normalize the final vector.

```text
norm = sqrt(Σ v_j^2)
embedding_j = v_j / norm
```

Because stored and query vectors are unit-normalized, retrieval similarity is their dot product,
equivalent to cosine similarity:

```text
similarity(q, d) = Σ(q_j × d_j)
```

The top five chunks are returned with document ID, filename, chunk position, score, and excerpt.
This is a transparent local retrieval baseline, not a semantic transformer embedding claim.

### 15.3 Retrieval query

The query includes organization-wide surveillance/severity/emergency concepts plus CV confidence,
impact score, vehicle count, and stopped-vehicle status. Camera location is intentionally excluded so
every policy uploaded by the organization remains applicable at every site. Retrieval also supplies
the actual incident location separately, configured contacts, notification preference, procedures,
and reviewed incidents.

## 16. Groq reasoning agent

Groq receives three explicit, size-bounded JSON evidence blocks:

1. `scanning_layer`: CV evidence, candidate sources, selected sensors, camera, location, timestamp,
   and a temporal summary of every frame (count, duration, minimum, maximum, mean, standard
   deviation, reliability, threshold crossings, and peak frame/time).
2. `verification_layer`: fused probability, contributions, adaptive threshold, override, evidence,
   and verification result.
3. `policy_retrieval`: policy excerpts, procedures, contacts, preferences, and reviewed incidents.

The lossless per-frame timeline remains in the incident audit, downloadable sensor JSON, and
analytics reconstruction. It is deliberately not duplicated into the LLM prompt. Retrieved policy
text is excerpt-limited, and historical incidents carry their weighted feature matches plus compact
scan/verification summaries instead of nested raw timelines. This keeps the request below the Groq
token-per-minute boundary without discarding decision-relevant evidence. Completion output is capped
at 1,800 tokens so the reasoning model can complete its internal reasoning and visible JSON without
truncation. Provider rate-limit details are converted into a concise operator-safe error instead
of exposing the raw SDK response in the dashboard. Common JSON structural drift is normalized and
validated locally without changing the core model decision. If the core decision is malformed, a
second Groq request repairs that same output under the strict schema before the pipeline fails.

The model is required to return JSON matching a strict Pydantic/JSON Schema contract. The output
contains severity, rationale items, response action, alert message, and an auditable memory-influence
object.

Allowed response actions are:

- `call`: urgent critical intervention;
- `message`: operator attention without a critical voice escalation;
- `none`: insignificant, suppressed, unverified, or non-escalated event.

Runtime validation rejects unsafe/inconsistent outputs, including:

- escalation of an unverified event;
- inconsistent memory-influence fields;
- escalation without a retrieved contact in live mode;
- response action inconsistent with notification fields;
- malformed JSON/schema output.

An unretrieved incident citation is treated as untrusted model output rather than a fatal pipeline
error: the ID is discarded and audited, then deterministic reconciliation uses only the actual
highest-similarity incident returned by the repository.

The dashboard displays the model-provided structured rationale. It does not expose or claim access to
private chain-of-thought. The visible rationale is the agent's intended audit explanation.

When Groq is not configured, the production app uses a clear unconfigured reasoning error. A
deterministic `ReasoningAgent` exists for automated tests and controlled fallback testing.

## 17. Planning and execution

Planning converts the decision into provider-neutral actions. Every processed incident normally
creates:

- dashboard alert;
- incident PDF report;
- optional voice call for `call`;
- optional WhatsApp message for `message`.

Messages are derived from the reasoning output and retrieved procedure context; they are not fixed
emergency templates.

### 17.1 PDF reports

ReportLab generates an A4 incident report containing detection ID, camera, location, time, severity,
agent message, rationale, retrieved policy, and procedures.

### 17.2 Twilio voice

Live voice uses Twilio's Calls API. The spoken TwiML contains Groq's alert message. Planning ensures
the camera location is added if it is missing from the message. Phone numbers are validated in E.164
format.

### 17.3 Twilio WhatsApp

WhatsApp delivery includes the alert, up to four policy-guided next steps, and a signed public URL for
the incident PDF. It requires a WhatsApp-enabled sender, public HTTPS backend URL, signing secret, and
valid provider/sandbox conditions.

### 17.4 Simulated execution mode

`SURVEILLANCE_EXECUTION_MODE=simulate` prevents external call/message requests while preserving real
CV, fusion, RAG, Groq reasoning, planning, PDF generation, persistence, and reviews. Simulated provider
actions are explicitly stored with status `simulated`, never `delivered`.

All delivery attempts are persisted. Provider failures are recorded as failures and are never shown
as successful.

## 18. Persistence model

SQLite tables currently include:

- organizations;
- users;
- authentication sessions;
- cameras;
- knowledge documents;
- knowledge chunks and embeddings;
- videos;
- processing jobs;
- incidents;
- agent audits;
- delivery records;
- incident reviews.

Migration `0012` adds the current sensor scenario and latest generated sensor sample to persistent
processing-job state. Full generated streams are stored as JSON files under the configured upload
directory. The incident audit stores the complete scanning and verification snapshots, so the
analytics page can reconstruct the decision without recalculating from mutable current settings.

Migration `0013` adds `learned_threshold_profiles`, keyed by organization and normalized location.
It stores the current learned threshold and the review versions already incorporated into it.

## 19. Authentication and tenant isolation

This is local demo authentication rather than a hosted identity provider.

- Passwords use PBKDF2-HMAC-SHA256 with a random 16-byte salt and 210,000 iterations.
- Session tokens are random and only SHA-256 token hashes are stored.
- Sessions expire after 12 hours by default.
- API keys entered during onboarding are fingerprinted; only SHA-256 fingerprint and last four
  characters are stored.
- Videos, policies, incidents, reviews, contacts, and retrieval are organization-scoped.
- Uploaded policies apply to every location in their organization. Location is still sent to Groq as
  incident context but is excluded from policy eligibility and the embedding query.

### 19.1 Map-selected locations

Onboarding and Operations share a Leaflet map backed by OpenStreetMap tiles. Operators explicitly
submit searches or click a pin; no autocomplete or periodic location polling occurs. A backend
Nominatim adapter sets an identifying User-Agent, caches repeated requests, serializes calls, and
enforces a minimum one-second interval. Its base URL is configurable so the public demo provider can
be replaced by a self-hosted or commercial service without changing presentation or domain code.

Secrets belong only in `.env`, which is excluded from Git. Any credential previously exposed in chat
or screenshots should be rotated before real deployment.

## 20. Server-Sent Events and live UI

SSE is used because the backend primarily sends one-way progress updates to the browser.

The processing-job event stream sends:

- persistent progress updates, including decoded frame count, percentage, detection count, scenario,
  and latest sensor readings;
- pipeline stage events as detection proceeds through verification, retrieval, reasoning, planning,
  execution, and memory.

The dashboard renders video playback, scan progress, latest smoke/audio values, the pipeline tracker,
and Groq's structured response. It polls no external model directly; all provider interactions remain
behind the backend boundary.

## 21. Decision Reconstruction analytics

Each incident can be selected from History & Analytics. The reconstruction includes:

- incident identity, camera, capture time, and source frame;
- CV-confidence, visual-impact, and fused-risk dials;
- source-comparison bars and selected threshold;
- visual probability equation;
- selected smoke/audio probability, reliability, freshness, and contribution;
- per-frame probability line charts;
- per-frame effective-reliability line charts;
- incident-frame marker and candidate/reliability gates;
- a frame-by-frame probability heatmap with exact hover values;
- cumulative log-odds probability journey;
- contribution waterfall and sigmoid result;
- guarded override and forced-demo-gate distinction;
- adaptive-threshold movement and reviewed-memory pressure;
- RAG chunk scores and excerpts;
- full evidence-fingerprint comparison with prior incidents;
- Groq severity, action, message, and structured rationale;
- evidence-to-action pipeline map;
- execution timeline, delivery status, PDF download, and human review form.

Older audits created before a field existed use an explicit fallback/empty state rather than inventing
historical values.

## 22. Important API endpoints

Authentication and onboarding:

```text
POST /api/v1/auth/signup
POST /api/v1/auth/login
POST /api/v1/auth/logout
GET  /api/v1/onboarding
PUT  /api/v1/onboarding
```

Knowledge:

```text
POST /api/v1/knowledge/policies
```

Videos and processing:

```text
POST /api/v1/videos
GET  /api/v1/videos
GET  /api/v1/videos/{video_id}/content
POST /api/v1/videos/{video_id}/process
GET  /api/v1/videos/{video_id}/sensor-stream
GET  /api/v1/processing-jobs/{job_id}
GET  /api/v1/processing-jobs/{job_id}/events
POST /api/v1/processing-jobs/{job_id}/cancel
POST /api/v1/processing-jobs/{job_id}/retry
```

Incidents and analytics:

```text
POST /api/v1/incidents/process
POST /api/v1/incidents/process/stream
GET  /api/v1/incidents
GET  /api/v1/incidents/{incident_id}
GET  /api/v1/incidents/{incident_id}/audit
GET  /api/v1/incidents/{incident_id}/deliveries
GET  /api/v1/incidents/{incident_id}/report
GET  /api/v1/incidents/{incident_id}/review
PUT  /api/v1/incidents/{incident_id}/review
GET  /api/v1/analytics/summary
```

Operations:

```text
GET /health
GET /ready
```

## 23. Main configuration values

All backend settings use the `SURVEILLANCE_` prefix.

```text
DATABASE_URL                         sqlite:///./surveillance.db
ACCIDENT_MODEL_PATH                  external best.pt path
ACCIDENT_CONFIDENCE_THRESHOLD        0.50
FRAME_SAMPLE_FPS                     2 visual frames/second
PLAYBACK_SPEED                       4
TEMPORAL_CLUSTER_GAP_SECONDS         5
VERIFICATION_THRESHOLD               0.68
ADAPTIVE_THRESHOLD_MINIMUM           0.60
ADAPTIVE_THRESHOLD_MAXIMUM           0.76
ADAPTIVE_THRESHOLD_MAXIMUM_ADJUSTMENT 0.08
ADAPTIVE_THRESHOLD_STABILIZER        3.0
ADAPTIVE_THRESHOLD_RECENCY_HALF_LIFE_DAYS 90
SENSOR_CANDIDATE_PROBABILITY         0.70
SENSOR_CANDIDATE_RELIABILITY         0.50
SENSOR_OVERRIDE_PROBABILITY          0.92
SENSOR_OVERRIDE_RELIABILITY          0.80
GROQ_MODEL                           openai/gpt-oss-20b by default
EXECUTION_MODE                       live or simulate
SESSION_TTL_HOURS                    12
```

Provider credentials are intentionally omitted from this document.

## 24. Evaluation metrics

The included test-video set is a small functional regression set, not a statistically valid claim of
general accuracy. At confidence threshold 0.50, its recorded results are:

```text
true positives  = 4
false positives = 0
true negatives  = 3
false negatives = 3
precision       = 1.0000
recall          = 0.5714
F1              = 0.7273
```

Formulas:

```text
precision = TP / (TP + FP)
recall    = TP / (TP + FN)
F1        = 2 × precision × recall / (precision + recall)
accuracy  = (TP + TN) / (TP + TN + FP + FN)
specificity = TN / (TN + FP)
false-positive rate = FP / (FP + TN)
```

The repository explicitly warns not to present the functional-set values as deployment accuracy.

For a defensible research evaluation, use a larger independently labeled dataset and report:

- precision, recall, F1, sensitivity, and specificity;
- confusion matrix;
- precision-recall curve and threshold selection;
- false alarms per camera-hour;
- Brier score and calibration error for fused probabilities;
- performance with missing sensors;
- performance by lighting/weather/site;
- override frequency and correctness;
- adaptive-threshold movement and review agreement;
- end-to-end response latency.

## 25. Current automated verification status

At the time this context file was generated:

- 87 Python backend/unit/integration tests pass;
- 11 React/Vitest tests pass;
- Ruff checks pass;
- ESLint checks pass;
- TypeScript compilation passes;
- Vite production build passes;
- database migration level is `0013`;
- backend health endpoint returns OK;
- dashboard development server returns HTTP 200.

## 26. Recommended demonstration sequence

1. Start FastAPI and the Vite dashboard.
2. Sign in to the local Sentrix account.
3. Confirm camera, location, emergency contact, notification preference, and agent key fingerprint.
4. Upload the demo policy PDF.
5. Upload an accident test video.
6. Start scanning.
7. Show that each source frame creates live smoke/audio readings.
8. Show CV candidates and the selected sensor frame entering verification.
9. Follow verification, RAG, Groq reasoning, planning, execution, and memory.
10. Download the generated per-frame sensor JSON after execution.
11. Open History & Analytics and select the new incident.
12. Explain the timeline graphs, fusion math, adaptive threshold, policy evidence, and decision flow.
13. Submit a human review.
14. Reprocess the same stored video and location to demonstrate reviewed-memory comparison and
    bounded threshold influence.
15. Download the incident PDF.

## 27. Honest limitations

- Smoke and audio data are synthetic and are not measurements inferred from video pixels.
- The generator demonstrates system behavior; it does not establish real sensor accuracy.
- Impact score is currently an adapter mapping, not a calibrated physical collision-severity model.
- The local hash embedding is transparent and offline but less semantically capable than a trained
  sentence-embedding model.
- Current fusion coefficients are expert-initialized priors, not coefficients fitted to synchronized
  field data.
- The small included clip set is for regression testing, not generalization claims.
- Twilio delivery depends on provider account state, number capabilities, geographic permissions,
  WhatsApp sandbox/template/window rules, and public HTTPS report access.
- Uploaded footage processing is local and synchronous within a background task; production scale
  would require a durable queue, object storage, worker processes, and PostgreSQL.
- The demo login system is suitable for a local prototype, not a complete enterprise IAM solution.
- Human-reviewed memory performs bounded retrieval and threshold adjustment; it is not online neural
  model retraining.

## 28. Future extensions

- Replace synthetic streams with timestamp-synchronized MQTT/IoT adapters.
- Calibrate sensor likelihoods and fusion coefficients using labeled real-world data.
- Use temporal video models or tracking instead of independent sampled YOLO frames.
- Add transformer embeddings with a local vector database while retaining citations.
- Add camera/site-specific calibration and drift monitoring.
- Add a durable task queue and distributed GPU workers.
- Move persistence from SQLite to PostgreSQL for deployment.
- Add signed object storage for videos, reports, and sensor streams.
- Add role-based access, stronger IAM, retention policies, and privacy redaction.
- Add formal agent and retrieval evaluation sets.
- Validate live Twilio calls and WhatsApp PDF delivery under the intended demonstration account.

## 29. One-paragraph report summary

Sentrix is a local-first, context-aware and risk-aware AI surveillance framework that processes uploaded CCTV footage
with a real YOLO accident detector and augments each decoded frame with an explicitly synthetic,
video-seeded smoke/audio sensor stream. Multimodal candidates enter a transparent logistic fusion
model with reliability decay, evidence agreement, contradiction suppression, and guarded override.
The baseline verification boundary is adjusted only slightly through a bounded, recency-weighted
model of similar human-reviewed incidents. The verified event, complete temporal sensor evidence,
retrieved policy excerpts, procedures, contacts, and reviewed memory are supplied to a Groq agent
under a strict structured-output contract. The resulting action plan drives dashboard alerts, PDF
reports, and optional Twilio voice or WhatsApp delivery, while every input, formula, decision,
execution result, and human correction is retained for interactive decision reconstruction.
