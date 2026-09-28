from __future__ import annotations

from collections.abc import Callable, Iterator

from .agents import (
    AuditAgent,
    ExecutionAgent,
    MemoryAgent,
    PlanningAgent,
    RetrievalAgent,
    VerificationAgent,
)
from .domain.models import (
    Detection,
    LearnedThresholdProfile,
    PipelineResult,
    Stage,
    StageEvent,
    structured,
)
from .ports import ReasoningService, ThresholdProfileRepository
from .verification import AdaptiveThresholdModel


class IncidentOrchestrator:
    def __init__(
        self,
        verification: VerificationAgent,
        retrieval: RetrievalAgent,
        reasoning: ReasoningService,
        planning: PlanningAgent,
        execution: ExecutionAgent,
        memory: MemoryAgent,
        audit: AuditAgent | None = None,
        adaptive_threshold: AdaptiveThresholdModel | None = None,
        threshold_profiles: ThresholdProfileRepository | None = None,
    ) -> None:
        self.verification = verification
        self.retrieval = retrieval
        self.reasoning = reasoning
        self.planning = planning
        self.execution = execution
        self.memory = memory
        self.audit = audit
        self.adaptive_threshold = adaptive_threshold or AdaptiveThresholdModel()
        self.threshold_profiles = threshold_profiles

    def process(
        self, detection: Detection, on_event: Callable[[StageEvent], None] | None = None
    ) -> PipelineResult:
        collected: list[StageEvent] = []
        for event in self.stream(detection):
            collected.append(event)
            if on_event is not None:
                on_event(event)
        events = tuple(collected)
        memory_payload = events[-1].payload
        execution_payload = events[-2].payload
        status = "completed" if not execution_payload["failed_actions"] else "completed_with_errors"
        return PipelineResult(str(memory_payload["incident_id"]), status, events)

    def stream(self, detection: Detection) -> Iterator[StageEvent]:
        yield StageEvent(Stage.DETECTION, structured(detection))
        verification = self.verification.run(detection)
        context = self.retrieval.run(detection)
        profile = (
            self.threshold_profiles.get(detection.organization_id, detection.location)
            if self.threshold_profiles is not None
            else None
        )
        verification = self.adaptive_threshold.apply(
            verification,
            context,
            detection.occurred_at,
            learned_baseline=profile.threshold if profile else None,
            applied_review_versions=profile.applied_review_versions if profile else (),
        )
        if self.threshold_profiles is not None and verification.threshold_profile_updated:
            self.threshold_profiles.save(
                LearnedThresholdProfile(
                    organization_id=detection.organization_id or "__local__",
                    location=detection.location,
                    threshold=verification.decision_threshold,
                    applied_review_versions=verification.threshold_applied_review_versions,
                )
            )
        yield StageEvent(Stage.VERIFICATION, structured(verification))
        yield StageEvent(Stage.RETRIEVAL, structured(context))
        decision = self.reasoning.run(detection, verification, context)
        yield StageEvent(Stage.REASONING, structured(decision))
        plan = self.planning.run(decision, context, detection)
        yield StageEvent(Stage.PLANNING, structured(plan))
        execution = self.execution.run(plan)
        yield StageEvent(Stage.EXECUTION, structured(execution))
        memory = self.memory.run(detection, decision)
        if self.audit is not None:
            self.audit.run(memory, context, decision, plan, execution, detection, verification)
        yield StageEvent(Stage.MEMORY, structured(memory))
