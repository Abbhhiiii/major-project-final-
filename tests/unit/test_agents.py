from packages.surveillance.adapters import LocalContextRepository
from packages.surveillance.agents import PlanningAgent, ReasoningAgent, VerificationAgent
from packages.surveillance.domain.models import Decision, Detection, IncidentContext, Severity


def test_explicit_response_routes_to_only_selected_channel():
    context = LocalContextRepository().retrieve(Detection("cam", 0.9, 1, False, 0.9, "Gate"))
    for response, expected in [
        ("call", "voice_alert"),
        ("message", "whatsapp_alert"),
        ("none", None),
    ]:
        decision = Decision(
            Severity.HIGH,
            ("Policy applied",),
            response != "none",
            "Review at Gate",
            response_action=response,
        )
        actions = PlanningAgent().run(decision, context).actions
        external = [a.kind for a in actions if a.kind != "dashboard_alert"]
        assert external == ([expected] if expected else [])


def test_planning_carries_policy_context_into_delivery() -> None:
    detection = Detection("cam", 0.9, 1, False, 0.9, "North Gate")
    context = IncidentContext(
        ("Critical policy",), ("+919876543210",), ("Clear the access route",), 0
    )
    decision = Decision(
        Severity.CRITICAL, ("Policy applied",), True, "Verified collision", response_action="call"
    )

    voice = next(
        action
        for action in PlanningAgent().run(decision, context, detection).actions
        if action.kind == "voice_alert"
    )

    assert "North Gate" in voice.message
    assert voice.details["policies"] == ["Critical policy"]
    assert voice.details["procedures"] == ["Clear the access route"]


def test_demo_planning_uses_labeled_target_when_contact_is_missing() -> None:
    context = IncidentContext(("Critical policy",), (), ("Clear the access route",), 0)
    decision = Decision(
        Severity.CRITICAL, ("Policy applied",), True, "Verified collision", response_action="call"
    )

    actions = PlanningAgent(simulation_mode=True).run(decision, context).actions

    voice = next(action for action in actions if action.kind == "voice_alert")
    assert voice.target == "demo-emergency-contact"


def test_verification_combines_independent_evidence() -> None:
    detection = Detection("cam-1", 0.9, 2, True, 0.8, "MG Road")
    result = VerificationAgent().run(detection)
    assert result.verified is True
    assert result.score == result.fused_probability
    assert result.score >= result.decision_threshold
    assert "vehicle remained stopped" in result.evidence


def test_demo_acceptance_preserves_raw_fusion_probability() -> None:
    detection = Detection("cam-2", 0.2, 1, False, 0.1, "Market Road")
    result = VerificationAgent(force_accept=True).run(detection)

    assert result.verified is True
    assert result.score == result.fused_probability
    assert result.fused_probability < result.decision_threshold
    assert "false-alarm gate forced accepted" in result.evidence[-1]


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
