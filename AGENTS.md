# Agentic Smart Surveillance Platform

## Product goal

Build a reliable final-year demo that turns uploaded CCTV footage into a simulated live feed, detects road accidents, verifies events, retrieves policy and historical context, reasons, plans, executes alerts, and stores incident memory.

## Engineering priorities

1. Demo reliability and clarity.
2. Simple, maintainable layered architecture.
3. Complete vertical slices instead of placeholder modules.
4. Local-first operation; only Twilio requires external connectivity.
5. Strong typing, validation, logging, error handling, and tests.

## Required pipeline

Detection -> Verification -> Context retrieval -> Reasoning -> Planning -> Execution -> Memory

Agents must have one responsibility, return structured JSON, and remain independently testable. Retrieved policies, contacts, procedures, prior incidents, and preferences must influence decisions. Twilio messages must be derived from reasoning output, never hardcoded.

## Architecture boundaries

- Presentation: web dashboard and mobile companion.
- Application: use cases and orchestration entry points.
- Agent: orchestrator, verification, retrieval, reasoning, planning, execution, and memory agents.
- Knowledge: RAG ingestion, retrieval, policy/contact/procedure sources.
- Execution: dashboard events, Twilio calls, PDF reports, incident and analytics updates.
- Infrastructure: configuration, providers, queues, logging, external integrations.
- Data: persistence models, repositories, and migrations.
- Perception: video simulation, CV adapter, detection normalization.
- Memory: historical incidents and agent decision records.

Dependencies must point inward: domain code must not import web frameworks, databases, Twilio, or model-provider SDKs.

## Development conventions

- Explain each new module's purpose, architectural layer, and approach before implementing it.
- Keep files focused and avoid duplicated business logic.
- Use environment variables for secrets and environment-specific values.
- Include unit tests for domain and agent logic and integration tests for boundaries.
- Do not commit secrets, generated footage, reports, model weights, or local databases.
- Prefer deterministic fallbacks so the core demo remains usable without network access.
- Maintain an architecture decision record when a durable technology choice changes.

## Initial technology baseline

- Backend and agents: Python 3.11+, FastAPI, Pydantic, SQLAlchemy, Alembic.
- Demo database: SQLite; preserve repository boundaries for later PostgreSQL use.
- Dashboard: React, TypeScript, Vite, Tailwind CSS.
- Live updates: Server-Sent Events initially; use WebSockets only if bidirectional realtime behavior becomes necessary.
- RAG: local embeddings and a lightweight local vector store selected during the knowledge-layer milestone.
- Testing: pytest for Python and Vitest/Playwright for the dashboard.

