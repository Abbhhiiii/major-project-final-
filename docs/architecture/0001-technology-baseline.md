# ADR 0001: Initial technology baseline

- Status: Accepted
- Date: 2026-08-02

## Decision

Use a Python/FastAPI backend, React/TypeScript dashboard, SQLite demo database behind SQLAlchemy repositories, and deterministic local agent implementations with replaceable AI-provider adapters.

Use Server-Sent Events for one-way pipeline updates to the dashboard. Introduce a background queue only when video processing demonstrates a concrete need for work isolation.

## Rationale

Python provides the shortest integration path for computer vision, local retrieval, PDF tooling, and AI orchestration. FastAPI and Pydantic provide typed HTTP contracts with little ceremony. SQLite removes database setup risk during a live demo, while SQLAlchemy and migrations keep a PostgreSQL upgrade possible. React and TypeScript are well suited to the animated reasoning pipeline and analytics interface. Deterministic agent fallbacks make the demo resilient when an external model is unavailable.

## Consequences

Long-running video inference must not block API request handlers. Provider-specific code must remain behind interfaces. The application will optimize for one-machine demo operation before adding distributed infrastructure.

