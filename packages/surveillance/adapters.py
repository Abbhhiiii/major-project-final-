from __future__ import annotations

from dataclasses import dataclass, field

from .domain.models import (
    Action,
    AgentAudit,
    Detection,
    IncidentContext,
    IncidentMemory,
    LearnedThresholdProfile,
)


@dataclass
class LocalContextRepository:
    """Deterministic seed knowledge used when no RAG provider is configured."""

    def retrieve(self, detection: Detection) -> IncidentContext:
        return IncidentContext(
            policies=("Notify emergency contacts for verified high-severity accidents",),
            contacts=("demo-emergency-dispatch",),
            procedures=("Confirm location", "Alert dashboard", "Escalate severe incidents"),
            prior_incident_count=0,
            preferences=("Prefer voice alert for high-severity incidents",),
        )


@dataclass
class RecordingActionExecutor:
    executed: list[Action] = field(default_factory=list)

    def execute(self, action: Action) -> None:
        self.executed.append(action)


@dataclass
class InMemoryIncidentRepository:
    incidents: list[IncidentMemory] = field(default_factory=list)

    def save(self, memory: IncidentMemory) -> None:
        self.incidents.append(memory)

    def get(self, incident_id: str, organization_id: str | None = None) -> IncidentMemory | None:
        return next(
            (
                incident
                for incident in self.incidents
                if incident.incident_id == incident_id
                and (organization_id is None or incident.organization_id == organization_id)
            ),
            None,
        )

    def list_recent(
        self, limit: int = 50, organization_id: str | None = None
    ) -> list[IncidentMemory]:
        incidents = [
            item
            for item in self.incidents
            if organization_id is None or item.organization_id == organization_id
        ]
        return sorted(incidents, key=lambda item: item.stored_at, reverse=True)[:limit]

    def severity_counts(self, organization_id: str | None = None) -> dict[str, int]:
        counts: dict[str, int] = {}
        for incident in self.list_recent(len(self.incidents), organization_id):
            counts[incident.severity.value] = counts.get(incident.severity.value, 0) + 1
        return counts


@dataclass
class InMemoryAuditRepository:
    audits: list[AgentAudit] = field(default_factory=list)

    def save(self, audit: AgentAudit) -> None:
        self.audits.append(audit)

    def get_for_incident(self, incident_id: str) -> AgentAudit | None:
        return next((item for item in self.audits if item.incident_id == incident_id), None)


@dataclass
class InMemoryThresholdProfileRepository:
    profiles: dict[tuple[str, str], LearnedThresholdProfile] = field(default_factory=dict)

    def get(self, organization_id: str | None, location: str) -> LearnedThresholdProfile | None:
        return self.profiles.get(self._key(organization_id, location))

    def save(self, profile: LearnedThresholdProfile) -> None:
        self.profiles[self._key(profile.organization_id, profile.location)] = profile

    @staticmethod
    def _key(organization_id: str | None, location: str) -> tuple[str, str]:
        return organization_id or "__local__", " ".join(location.strip().casefold().split())
