from packages.surveillance.adapters import LocalContextRepository
from packages.surveillance.agents import ReasoningAgent, VerificationAgent
from packages.surveillance.domain.models import Detection, Severity


def test_verification_combines_independent_evidence() -> None:
    detection = Detection("cam-1", 0.9, 2, True, 0.8, "MG Road")
    result = VerificationAgent().run(detection)
    assert result.verified is True
    assert result.score == 0.88
    assert "vehicle remained stopped" in result.evidence


def test_reasoning_uses_retrieved_policy_and_history() -> None:
    detection = Detection("cam-1", 0.9, 2, True, 0.8, "MG Road")
    verification = VerificationAgent().run(detection)
    context = LocalContextRepository().retrieve(detection)
    decision = ReasoningAgent().run(detection, verification, context)
    assert decision.severity == Severity.HIGH
    assert decision.notify_emergency_services is True
    assert "Applied policy" in decision.rationale[1]
    assert "Next procedure" in decision.rationale[2]
    assert "0 prior incidents" in decision.rationale[3]


def test_low_confidence_event_is_suppressed() -> None:
    detection = Detection("cam-2", 0.2, 1, False, 0.1, "Market Road")
    verification = VerificationAgent().run(detection)
    context = LocalContextRepository().retrieve(detection)
    decision = ReasoningAgent().run(detection, verification, context)
    assert verification.verified is False
    assert decision.severity == Severity.LOW
    assert decision.notify_emergency_services is False
