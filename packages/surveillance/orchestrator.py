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
from .domain.models import Detection, PipelineResult, Stage, StageEvent, structured
from .ports import ReasoningService


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
    ) -> None:
        self.verification = verification
        self.retrieval = retrieval
        self.reasoning = reasoning
        self.planning = planning
        self.execution = execution
        self.memory = memory
        self.audit = audit

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
        yield StageEvent(Stage.VERIFICATION, structured(verification))
        context = self.retrieval.run(detection)
        yield StageEvent(Stage.RETRIEVAL, structured(context))
        decision = self.reasoning.run(detection, verification, context)
        yield StageEvent(Stage.REASONING, structured(decision))
        plan = self.planning.run(decision, context, detection)
        yield StageEvent(Stage.PLANNING, structured(plan))
        execution = self.execution.run(plan)
        yield StageEvent(Stage.EXECUTION, structured(execution))
        memory = self.memory.run(detection, decision)
        if self.audit is not None:
            self.audit.run(memory, context, decision, plan, execution)
        yield StageEvent(Stage.MEMORY, structured(memory))
