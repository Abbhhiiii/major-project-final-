from datetime import UTC, datetime, timedelta

import pytest

from packages.surveillance.domain.models import IncidentContext, Verification
from packages.surveillance.verification import AdaptiveThresholdModel

REFERENCE = datetime(2026, 9, 27, tzinfo=UTC)


def verification(probability: float = 0.70, *, forced_accept: bool = False) -> Verification:
    return Verification(
        detection_id="current",
        verified=probability >= 0.68 or forced_accept,
        score=probability,
        fused_probability=probability,
        decision_threshold=0.68,
        evidence=("fusion complete",),
        forced_accept=forced_accept,
    )


def context(*reviews: dict) -> IncidentContext:
    return IncidentContext((), (), (), len(reviews), reviewed_incidents=reviews)


def reviewed(
    *,
    incident_id: str = "previous",
    similarity: float = 0.9,
    days_old: float = 0,
    false_alarm: bool = False,
    original_severity: str = "high",
    original_action: str = "message",
    reviewed_severity: str = "high",
    reviewed_action: str = "message",
) -> dict:
    return {
        "incident_id": incident_id,
        "influence_weight": similarity,
        "reviewed_at": (REFERENCE - timedelta(days=days_old)).isoformat(),
        "false_alarm": false_alarm,
        "reviewed_severity": reviewed_severity,
        "response_action": reviewed_action,
        "reason": "Human-reviewed outcome",
        "original_decision": {
            "severity": original_severity,
            "response_action": original_action,
        },
    }


def test_no_reviewed_memory_keeps_baseline_threshold() -> None:
    result = AdaptiveThresholdModel().apply(verification(), context(), REFERENCE)

    assert result.base_decision_threshold == 0.68
    assert result.decision_threshold == 0.68
    assert result.threshold_adjustment == 0
    assert result.threshold_factors == ()
    assert result.baseline_verified is True
    assert result.adaptive_verified is True


def test_false_alarm_raises_threshold_and_can_suppress_borderline_event() -> None:
    result = AdaptiveThresholdModel().apply(
        verification(0.69),
        context(reviewed(false_alarm=True)),
        REFERENCE,
    )

    expected_delta = 0.08 * 0.9 / (3 + 0.9)
    assert result.threshold_adjustment == pytest.approx(expected_delta, abs=1e-4)
    assert result.decision_threshold == pytest.approx(0.6985, abs=1e-4)
    assert result.threshold_factors[0]["effect"] == "raise_false_alarm"
    assert result.threshold_factors[0]["direction"] == 1
    assert result.baseline_verified is True
    assert result.adaptive_verified is False
    assert result.verified is False


def test_underestimated_incident_lowers_threshold() -> None:
    result = AdaptiveThresholdModel().apply(
        verification(0.67),
        context(
            reviewed(
                original_severity="low",
                original_action="none",
                reviewed_severity="critical",
                reviewed_action="call",
            )
        ),
        REFERENCE,
    )

    assert result.decision_threshold < 0.68
    assert result.threshold_factors[0]["effect"] == "lower_underestimated"
    assert result.threshold_factors[0]["direction"] == -1
    assert result.baseline_verified is False
    assert result.adaptive_verified is True


def test_correct_review_stabilizes_denominator_without_moving_threshold() -> None:
    result = AdaptiveThresholdModel().apply(
        verification(),
        context(reviewed()),
        REFERENCE,
    )

    assert len(result.threshold_factors) == 1
    assert result.threshold_factors[0]["effect"] == "unchanged"
    assert result.threshold_factors[0]["weight"] == 0.9
    assert result.threshold_factors[0]["signed_weight"] == 0
    assert result.threshold_adjustment == 0


def test_recency_weight_uses_ninety_day_half_life() -> None:
    result = AdaptiveThresholdModel().apply(
        verification(),
        context(reviewed(similarity=0.8, days_old=90, false_alarm=True)),
        REFERENCE,
    )

    factor = result.threshold_factors[0]
    assert factor["recency"] == pytest.approx(0.5)
    assert factor["weight"] == pytest.approx(0.4)


def test_forced_demo_gate_does_not_hide_raw_adaptive_outcome() -> None:
    result = AdaptiveThresholdModel().apply(
        verification(0.2, forced_accept=True),
        context(reviewed(false_alarm=True)),
        REFERENCE,
    )

    assert result.baseline_verified is False
    assert result.adaptive_verified is False
    assert result.verified is True
    assert result.forced_accept is True


def test_learned_threshold_becomes_next_baseline_without_reapplying_review() -> None:
    memory = context(reviewed(similarity=0.8, false_alarm=True))
    model = AdaptiveThresholdModel()

    first = model.apply(verification(0.72), memory, REFERENCE)
    second = model.apply(
        verification(0.72),
        memory,
        REFERENCE + timedelta(days=1),
        learned_baseline=first.decision_threshold,
        applied_review_versions=first.threshold_applied_review_versions,
    )

    assert first.threshold_profile_updated is True
    assert first.threshold_new_review_count == 1
    assert first.decision_threshold > 0.68
    assert second.base_decision_threshold == first.decision_threshold
    assert second.decision_threshold == first.decision_threshold
    assert second.threshold_adjustment == 0
    assert second.threshold_profile_updated is False
    assert second.threshold_factors[0]["already_learned"] is True
    assert second.threshold_factors[0]["applied_to_baseline"] is False
