from packages.surveillance.domain.memory_influence import ReviewedMemoryDecisionModel
from packages.surveillance.domain.models import IncidentContext, Severity


def context(*reviews: dict) -> IncidentContext:
    return IncidentContext((), (), (), len(reviews), reviewed_incidents=reviews)


def review(similarity: float, severity: str, action: str, **extra) -> dict:
    return {
        "incident_id": "reviewed-1",
        "similarity": similarity,
        "influence_weight": similarity,
        "reviewed_severity": severity,
        "response_action": action,
        **extra,
    }


def test_exact_match_completely_adopts_human_review() -> None:
    result = ReviewedMemoryDecisionModel().reconcile(
        Severity.LOW,
        "none",
        context(review(1.0, "high", "message")),
    )

    assert result is not None
    assert result.final_severity == Severity.HIGH
    assert result.final_action == "message"
    assert result.current_weight == 0
    assert result.similarity == 1
    assert result.audit()["weight"] == 1


def test_partial_match_interpolates_review_and_current_draft() -> None:
    result = ReviewedMemoryDecisionModel().reconcile(
        Severity.LOW,
        "none",
        context(review(0.75, "critical", "call")),
    )

    assert result is not None
    assert result.severity_score == 2.25
    assert result.action_score == 1.5
    assert result.final_severity == Severity.HIGH
    assert result.final_action == "call"
    assert result.current_weight == 0.25


def test_similar_upward_high_review_cannot_collapse_below_medium() -> None:
    result = ReviewedMemoryDecisionModel().reconcile(
        Severity.LOW,
        "none",
        context(review(0.7, "high", "message")),
    )

    assert result is not None
    assert result.reviewed_severity_floor == Severity.MEDIUM
    assert result.final_severity in {Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL}
    assert result.final_action == "message"


def test_false_alarm_review_always_targets_low_and_none() -> None:
    result = ReviewedMemoryDecisionModel().reconcile(
        Severity.CRITICAL,
        "call",
        context(review(1.0, "critical", "call", false_alarm=True)),
    )

    assert result is not None
    assert result.final_severity == Severity.LOW
    assert result.final_action == "none"
    assert result.effect == "lowered"
