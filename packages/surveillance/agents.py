from __future__ import annotations

import logging
from uuid import uuid4

from .domain.models import (
    Action,
    AgentAudit,
    Decision,
    Detection,
    ExecutionResult,
    IncidentContext,
    IncidentMemory,
    IncidentPlan,
    Severity,
    Verification,
    structured,
)
from .ports import ActionExecutor, AuditRepository, ContextRepository, MemoryRepository

logger = logging.getLogger(__name__)


class VerificationAgent:
    def __init__(self, force_accept: bool = False) -> None:
        self.force_accept = force_accept

    def run(self, detection: Detection) -> Verification:
        score = round(
            detection.confidence * 0.5
            + detection.impact_score * 0.35
            + (0.15 if detection.stopped_vehicle else 0),
            3,
        )
        evidence = [f"detector confidence {detection.confidence:.2f}"]
        if detection.impact_score >= 0.6:
            evidence.append("high visual impact score")
        if detection.stopped_vehicle:
            evidence.append("vehicle remained stopped")
        if self.force_accept:
            evidence.append("false-alarm gate forced accepted by demo configuration")
            return Verification(detection.detection_id, True, max(score, 0.99), tuple(evidence))
        return Verification(detection.detection_id, score >= 0.65, score, tuple(evidence))


class RetrievalAgent:
    def __init__(self, repository: ContextRepository) -> None:
        self.repository = repository

    def run(self, detection: Detection) -> IncidentContext:
        return self.repository.retrieve(detection)


class ReasoningAgent:
    def run(
        self, detection: Detection, verification: Verification, context: IncidentContext
    ) -> Decision:
        if not verification.verified:
            return Decision(
                Severity.LOW,
                ("Evidence did not meet the verification threshold.",),
                False,
                f"Unverified road event at {detection.location}; operator review requested.",
            )

        combined = max(verification.score, detection.impact_score)
        if combined >= 0.9:
            severity = Severity.CRITICAL
        elif combined >= 0.75:
            severity = Severity.HIGH
        else:
            severity = Severity.MEDIUM
        emergency = severity in {Severity.HIGH, Severity.CRITICAL} and bool(context.contacts)
        rationale = (
            f"Verified with score {verification.score:.2f}.",
            f"Applied policy: {context.policies[0] if context.policies else 'default response policy'}.",
            f"Next procedure: {context.procedures[0] if context.procedures else 'operator review'}.",
            f"Found {context.prior_incident_count} prior incidents near this location.",
        )
        message = (
            f"{severity.value.upper()} verified road accident at {detection.location}. "
            f"Camera {detection.camera_id}; {detection.vehicle_count} vehicle(s) observed."
        )
        return Decision(severity, rationale, emergency, message)


class PlanningAgent:
    def run(
        self, decision: Decision, context: IncidentContext, detection: Detection | None = None
    ) -> IncidentPlan:
        details: dict[str, object] = {}
        if detection is not None:
            details = {
                "detection_id": detection.detection_id,
                "camera_id": detection.camera_id,
                "location": detection.location,
                "occurred_at": detection.occurred_at.isoformat(),
                "severity": decision.severity.value,
                "rationale": list(decision.rationale),
            }
        actions = [
            Action("dashboard_alert", "operations-dashboard", decision.alert_message, details)
        ]
        if detection is not None:
            actions.append(
                Action("pdf_report", detection.detection_id, decision.alert_message, details)
            )
        voice_preferred = any("voice" in preference.lower() for preference in context.preferences)
        if decision.notify_emergency_services and voice_preferred:
            actions.extend(
                Action(
                    "voice_alert",
                    contact,
                    decision.alert_message,
                    {"detection_id": detection.detection_id if detection else ""},
                )
                for contact in context.contacts
            )
        return IncidentPlan(tuple(actions))


class ExecutionAgent:
    def __init__(self, executor: ActionExecutor) -> None:
        self.executor = executor

    def run(self, plan: IncidentPlan) -> ExecutionResult:
        successful: list[str] = []
        failed: list[str] = []
        for action in plan.actions:
            label = f"{action.kind}:{action.target}"
            try:
                self.executor.execute(action)
                successful.append(label)
            except Exception:
                logger.exception("Action execution failed", extra={"action": label})
                failed.append(label)
        return ExecutionResult(tuple(successful), tuple(failed))


class MemoryAgent:
    def __init__(self, repository: MemoryRepository) -> None:
        self.repository = repository

    def run(self, detection: Detection, decision: Decision) -> IncidentMemory:
        memory = IncidentMemory(
            str(uuid4()),
            detection.detection_id,
            decision.severity,
            detection.location,
            decision.rationale,
            decision.alert_message,
            detection.organization_id,
            detection.source_video_id,
            detection.frame_timestamp_ms,
        )
        self.repository.save(memory)
        return memory


class AuditAgent:
    def __init__(self, repository: AuditRepository) -> None:
        self.repository = repository

    def run(
        self,
        memory: IncidentMemory,
        context: IncidentContext,
        decision: Decision,
        plan: IncidentPlan,
        execution: ExecutionResult,
    ) -> AgentAudit:
        audit = AgentAudit(
            incident_id=memory.incident_id,
            detection_id=memory.detection_id,
            reasoning_provider=decision.provider,
            reasoning_model=decision.model,
            retrieval=structured(context),
            decision=structured(decision),
            plan=structured(plan),
            execution=structured(execution),
        )
        self.repository.save(audit)
        return audit
