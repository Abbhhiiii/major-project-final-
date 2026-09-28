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
from .verification import EvidenceFusionModel

logger = logging.getLogger(__name__)


class VerificationAgent:
    def __init__(
        self, force_accept: bool = False, fusion_model: EvidenceFusionModel | None = None
    ) -> None:
        self.force_accept = force_accept
        self.fusion_model = fusion_model or EvidenceFusionModel()

    def run(self, detection: Detection) -> Verification:
        result = self.fusion_model.evaluate(detection)
        evidence = list(result.evidence)
        if detection.stopped_vehicle:
            evidence.append("vehicle remained stopped")
        if self.force_accept:
            evidence.append("false-alarm gate forced accepted by demo configuration")
            return Verification(
                detection_id=detection.detection_id,
                verified=True,
                score=result.probability,
                evidence=tuple(evidence),
                fused_probability=result.probability,
                decision_threshold=result.threshold,
                override_source=result.override_source,
                contributions=result.contributions,
                forced_accept=True,
            )
        return Verification(
            detection_id=detection.detection_id,
            verified=result.verified,
            score=result.probability,
            evidence=tuple(evidence),
            fused_probability=result.probability,
            decision_threshold=result.threshold,
            override_source=result.override_source,
            contributions=result.contributions,
        )


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
    def __init__(self, simulation_mode: bool = False) -> None:
        self.simulation_mode = simulation_mode

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
                "policies": list(context.policies),
                "procedures": list(context.procedures),
                "evidence": [structured(item) for item in context.evidence],
            }
        actions = [
            Action("dashboard_alert", "operations-dashboard", decision.alert_message, details)
        ]
        if detection is not None:
            actions.append(
                Action("pdf_report", detection.detection_id, decision.alert_message, details)
            )
        delivery_targets = context.contacts or (
            ("demo-emergency-contact",) if self.simulation_mode else ()
        )
        voice_preferred = any("voice" in preference.lower() for preference in context.preferences)
        if decision.response_action == "call" or (
            decision.response_action is None
            and decision.notify_emergency_services
            and voice_preferred
        ):
            voice_message = decision.alert_message
            if detection is not None and detection.location.lower() not in voice_message.lower():
                voice_message = f"{voice_message} Location: {detection.location}."
            actions.extend(
                Action(
                    "voice_alert",
                    contact,
                    voice_message,
                    details,
                )
                for contact in delivery_targets
            )
        whatsapp_preferred = any(
            "whatsapp" in preference.lower() for preference in context.preferences
        )
        if decision.response_action == "message" or (
            decision.response_action is None
            and decision.notify_emergency_services
            and whatsapp_preferred
        ):
            actions.extend(
                Action(
                    "whatsapp_alert",
                    contact,
                    decision.alert_message,
                    details,
                )
                for contact in delivery_targets
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
        detection: Detection | None = None,
        verification: Verification | None = None,
    ) -> AgentAudit:
        audit = AgentAudit(
            incident_id=memory.incident_id,
            detection_id=memory.detection_id,
            reasoning_provider=decision.provider,
            reasoning_model=decision.model,
            retrieval={
                **structured(context),
                "scan_snapshot": structured(detection) if detection else {},
                "verification_snapshot": structured(verification) if verification else {},
            },
            decision=structured(decision),
            plan=structured(plan),
            execution=structured(execution),
        )
        self.repository.save(audit)
        return audit
