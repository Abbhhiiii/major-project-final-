# Agentic Smart Surveillance Platform

A local-first surveillance demonstration that converts uploaded CCTV footage into a simulated live stream and carries road-accident detections through verification, context retrieval, reasoning, planning, execution, and memory.

## Status

The deterministic incident pipeline, persistent backend, and first operations dashboard are implemented.
The dashboard supports local CCTV playback, simulated detections, an animated live reasoning trace,
incident history, and analytics. Computer vision, model-backed reasoning, RAG, Twilio, reporting,
and the mobile companion will be added as tested vertical slices.

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

Twilio is disabled by default. Set `SURVEILLANCE_TWILIO_ENABLED=true` together with the account SID,
auth token, and sender number to enable live calls. Offline voice actions are stored as
`simulated_offline`, including the exact reasoning-generated message that would be spoken.

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
