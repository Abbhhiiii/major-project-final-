# Agentic Smart Surveillance Platform

Sentrix is a local-first AI surveillance framework that converts uploaded CCTV footage into a simulated live stream and carries multimodal risk detections through verification, context retrieval, reasoning, planning, execution, and memory.

## Status

The complete local demo pipeline is implemented: real uploaded-video CV inference, per-frame synthetic
sensor streams, statistical verification, policy RAG, Groq reasoning, planning, PDF/report execution,
reviewed memory, and immersive decision reconstruction. Twilio voice and WhatsApp adapters are
implemented but require valid provider configuration and separate live-account validation.

## Run locally

Requires Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn apps.backend.main:app --reload
```

Submit a simulated normalized detection:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/incidents/process \
  -H 'content-type: application/json' \
  -d '{"camera_id":"junction-7","confidence":0.94,"vehicle_count":2,"stopped_vehicle":true,"impact_score":0.92,"location":"Airport Road"}'
```

Run the test suite with `pytest`. The API creates the local SQLite schema automatically for demo
reliability. Apply versioned migrations explicitly with `alembic upgrade head` in deployed setups.

Environment variables use the `SURVEILLANCE_` prefix; copy `.env.example` to `.env` to customize
the database URL or log level.

Additional backend endpoints:

- `POST /api/v1/incidents/process/stream` streams dashboard-ready pipeline events using SSE.
- `GET /api/v1/incidents` returns recent incident history.
- `GET /api/v1/incidents/{incident_id}` returns stored decision context for one incident.
- `GET /api/v1/analytics/summary` returns incident totals grouped by severity.
- `POST /api/v1/videos` validates and stores uploaded CCTV footage.
- `GET /api/v1/videos` returns the persistent video catalog.
- `GET /api/v1/videos/{video_id}/content` supports browser playback and range requests.
- `POST /api/v1/videos/{video_id}/detections` normalizes accident-model output and runs the agent pipeline.
- `POST /api/v1/videos/{video_id}/process` starts timestamp-paced OpenCV frame processing.
- `GET /api/v1/processing-jobs/{job_id}` returns persistent scan progress.
- `GET /api/v1/processing-jobs/{job_id}/events` streams scan progress using SSE.
- `POST /api/v1/auth/signup` and `POST /api/v1/auth/login` create mock local sessions.
- `GET/PUT /api/v1/onboarding` reads or configures the organization and camera.
- `POST /api/v1/knowledge/policies` stores, extracts, and chunks an authenticated policy PDF.
- `GET /api/v1/incidents/{incident_id}/deliveries` returns dashboard, report, and voice outcomes.
- `GET /api/v1/incidents/{incident_id}/report` downloads the generated PDF report.
- `GET /ready` reports whether every required real integration is configured.

Policy chunks receive deterministic local feature-hash embeddings and are ranked using cosine
similarity. Retrieval events expose the source filename, chunk position, relevance score, and excerpt
so the dashboard can show why a policy was selected without requiring network access.

The initial scan is multimodal: CV, smoke, and audio can independently create a candidate. A
sensor-only candidate carries zero visual evidence rather than a fabricated CV score. Verification
then uses a reliability-aware logistic evidence-fusion model. Visual confidence and impact,
plus optional smoke and audio probabilities, contribute to a fused risk probability. Reliability and
freshness discount weak sensor data; agreement adds evidence; trustworthy low auxiliary readings can
suppress a visual false alarm; and an exceptionally high, reliable sensor may trigger a guarded
override. Visual impact at or above 0.90 can also override when detector confidence is at least 0.75.
Groq receives compact complete-evidence summaries, the fusion result, and retrieved policy context as
three explicit structured inputs; lossless frame streams remain in the audit and analytics. Reviewed
incident severity/action is reconciled with Groq's current-evidence draft in direct proportion to
similarity, so a 100% match reproduces the reviewed result exactly and strong upward reviews enforce
a similarity-derived severity floor. When multiple reviewed incidents qualify, only the single
highest-similarity match influences the current pipeline. Adaptive thresholds persist per organization/location: a new
review version changes the baseline once, and that result becomes the following scan's baseline.
Demo sensor values are generated
for every decoded video frame by the local sensor-twin model and are clearly marked
`synthetic_live`. The complete generated stream becomes downloadable after pipeline execution.
Before each video scan, the operator selects `both_high`, `both_low`, `smoke_high`, `audio_high`, or
`randomized`; that selection is validated, persisted, audited, preserved on retry, and included in
the downloadable stream.

During an Operations demo, every synchronized sensor frame is emitted over SSE and shown in a live
timeline. The presentation then reveals and automatically focuses verification mathematics,
organization policy and reviewed-memory retrieval, Groq reasoning, action planning, execution, and
durable incident memory. The pacing is visual only; displayed evidence comes from the real pipeline.

Camera locations are selected with a Leaflet/OpenStreetMap map rather than free text. Explicit
searches and pin clicks resolve through a cached, rate-limited backend Nominatim adapter. Uploaded
policy PDFs are organization-wide: location remains part of the incident and agent context, but it
does not determine whether an uploaded policy applies.

Twilio is disabled by default. Set `SURVEILLANCE_TWILIO_ENABLED=true` together with the account SID,
either an auth token or matching API key credentials, and a voice-capable Twilio/verified sender
number to enable live calls. Contacts must use E.164 format. `call`, `message`, and `none` route to
voice, WhatsApp, and no external delivery respectively. Failed provider attempts are persisted as
failed delivery receipts; the platform never reports them as successful.

For a safe presentation run, set `SURVEILLANCE_EXECUTION_MODE=simulate`. Groq reasoning, policy
retrieval, verification, PDF generation, incident memory, and human-review memory remain real, while
voice and WhatsApp actions are stored with the explicit status `simulated` and no provider request is
made. Restore `live` before validating Twilio.

For WhatsApp PDF delivery, also enable `SURVEILLANCE_TWILIO_WHATSAPP_ENABLED`, configure a
WhatsApp-enabled Twilio sender, and set `SURVEILLANCE_PUBLIC_BASE_URL` to the public HTTPS origin
Twilio can use to fetch reports. `SURVEILLANCE_REPORT_LINK_SECRET` signs those media URLs. The
organization notification preference must contain `WhatsApp`; the onboarding UI sets voice and
WhatsApp by default. During Sandbox testing, the emergency-contact phone must join the Sandbox and
open the 24-hour customer-service window before a free-form alert with PDF media is sent.
Run `.venv/bin/python -m scripts.check_twilio_setup` to validate credentials and configuration without
placing a call or sending a message.

The live development configuration loads the discovered YOLOv8 checkpoint at
`Accident-Detection-and-Notification/ML part/best.pt`. Its embedded classes are `moderate` and
`severe`; uploaded-video processing sends sampled OpenCV frames directly to this model.

Until an accident-model adapter is configured, frame processing uses an observation-only detector:
it reads and paces real frames but deliberately emits no accident events. This avoids presenting a
fabricated heuristic as computer-vision inference.

### Dashboard

The dashboard requires Node.js 24 LTS or newer. In a second terminal:

```bash
cd apps/dashboard
npm install
npm run dev
```

Open `http://localhost:5173`. The frontend connects to `http://127.0.0.1:8000` by default. Set
`VITE_API_URL` when the backend runs elsewhere.

Dashboard checks:

```bash
npm run lint
npm test
npm run build
```

## Planned demo flow

```text
Uploaded CCTV video
  -> simulated live feed
  -> accident detector adapter
  -> normalized detection event
  -> verification agent
  -> policy and history retrieval
  -> reasoning agent
  -> planning agent
  -> execution agent
  -> dashboard / voice alert / PDF / incident history / analytics
  -> memory agent
```

## Repository layout

```text
apps/            Deployable FastAPI backend and React dashboard
packages/        Shared domain, agent, knowledge, and infrastructure modules
docs/            Architecture decisions and demo documentation
tests/           Cross-component and end-to-end tests
```

Core code lives under `packages/surveillance`, the HTTP boundary under `apps/backend`, the React
application under `apps/dashboard`, and backend tests under `tests`.
