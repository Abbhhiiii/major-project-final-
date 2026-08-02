# Product scope and incremental delivery plan

This document captures the original product brief as stable acceptance criteria. Work is delivered
as complete vertical slices so each milestone remains demonstrable and testable.

## Demo journey

1. Upload recorded CCTV footage.
2. Play it as a simulated live stream.
3. Normalize accident-model detections into domain events.
4. Verify evidence and suppress likely false alarms.
5. Retrieve policies, emergency contacts, procedures, prior incidents, and user preferences.
6. Reason about severity and response using the retrieved context.
7. Plan and execute dashboard, voice, reporting, logging, and analytics actions.
8. Store the incident and agent decisions as reusable memory.

Only Twilio voice delivery may require external connectivity. The remaining demo must have reliable
local fallbacks.

## User-facing acceptance criteria

- A professional, minimal dark dashboard supports footage upload and simulated-live playback.
- The reasoning panel animates Event Received, Verification, Policy Retrieval, Reasoning, Planning,
  and Execution so an audience can follow the system's decisions.
- Verified severe events can trigger a Twilio voice call whose wording comes from reasoning output.
- Each incident can produce a PDF report and appears in incident history and analytics.
- A mobile companion presents the key incident alert and status experience.

## Delivery milestones

1. **Runnable incident pipeline:** typed contracts, deterministic agents, structured stage events,
   local context, execution recording, and memory behind an HTTP API.
2. **Persistent backend:** SQLite repositories, migrations, incident/history APIs, structured logs,
   configuration, and server-sent stage events.
3. **Dashboard demo:** upload, video simulation, reasoning animation, incident history, and analytics.
4. **Perception integration:** accident-detector adapter, frame timestamps, event normalization, and
   false-alarm test footage.
5. **Knowledge and execution:** local RAG ingestion/retrieval, PDF reports, Twilio adapter, and
   deterministic offline fallbacks.
6. **Mobile companion and demo hardening:** focused alert/status experience, end-to-end tests,
   observability, seeded demo data, and presentation runbook.

## Current implementation status

| Capability | Status | Notes |
| --- | --- | --- |
| Seven-stage agent pipeline | Complete | Structured detection through memory events with deterministic local agents. |
| Verification and false-alarm suppression | Complete | Multi-signal verification threshold with test coverage. |
| Context-aware reasoning and planning | Complete foundation | Local policies, contacts, procedures, history, and preferences influence decisions; vector RAG is pending. |
| Incident persistence, history, analytics | Complete foundation | SQLite, SQLAlchemy, Alembic, history/detail APIs, and severity totals. |
| Live dashboard reasoning trace | Complete | React dashboard consumes SSE and visibly paces each stage. |
| CCTV upload and playback | Complete | Validated backend storage, persistent catalog, and HTTP range playback. |
| Perception normalization | Complete | Provider-neutral accident-model output is validated with video and frame provenance. |
| Simulated-live frame processing | Complete | OpenCV frame sampling, timestamp pacing, persistent progress jobs, and SSE status. |
| Mock authentication and onboarding | Complete | Organization signup/login, hashed credentials, camera setup, masked agent-key fingerprint, and policy upload. |
| Policy PDF retrieval | Complete | PDFs are retained locally, extracted/chunked, embedded offline, ranked by cosine relevance, and cited in reasoning events. |
| PDF incident reports | Complete | Each processed detection produces a downloadable report derived from decision context and rationale. |
| Twilio voice execution | Complete foundation | Dynamic TwiML calls are supported when enabled; offline runs are explicitly recorded as simulated deliveries. |
| Real accident-model inference | Complete | The discovered YOLOv8 `best.pt` runs directly on sampled frames with moderate/severe class mapping. |
| Neural embedding upgrade | Optional enhancement | Deterministic local feature-hash embeddings are complete; a neural adapter can improve semantic recall later. |
| Advanced analytics | Pending | Timeline, response latency, location trends, and false-positive metrics. |
| Mobile companion | Pending | Alert, acknowledgement, and incident status experience. |
| Demo hardening | Pending | End-to-end footage tests, model calibration, seeded demo, packaging, and runbook. |
