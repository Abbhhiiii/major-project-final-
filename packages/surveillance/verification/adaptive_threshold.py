from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from math import pow
from typing import ClassVar

from ..domain.models import IncidentContext, Verification


class AdaptiveThresholdModel:
    """Makes small, bounded threshold changes from comparable human-reviewed outcomes."""

    SEVERITY_RANK: ClassVar[dict[str, int]] = {
        "low": 0,
        "medium": 1,
        "high": 2,
        "critical": 3,
    }
    ACTION_RANK: ClassVar[dict[str, int]] = {"none": 0, "message": 1, "call": 2}

    def __init__(
        self,
        minimum: float = 0.60,
        maximum: float = 0.76,
        maximum_adjustment: float = 0.08,
        stabilizer: float = 3.0,
        recency_half_life_days: float = 90.0,
    ) -> None:
        if not 0 <= minimum <= maximum <= 1:
            raise ValueError("adaptive threshold bounds must be ordered probabilities")
        if maximum_adjustment < 0 or stabilizer <= 0 or recency_half_life_days <= 0:
            raise ValueError("adaptive threshold parameters must be positive")
        self.minimum = minimum
        self.maximum = maximum
        self.maximum_adjustment = maximum_adjustment
        self.stabilizer = stabilizer
        self.recency_half_life_days = recency_half_life_days

    def apply(
        self,
        verification: Verification,
        context: IncidentContext,
        reference_time: datetime | None = None,
        learned_baseline: float | None = None,
        applied_review_versions: tuple[str, ...] = (),
    ) -> Verification:
        reference = reference_time or datetime.now(UTC)
        if reference.tzinfo is None:
            reference = reference.replace(tzinfo=UTC)
        factors = tuple(
            factor
            for review in context.reviewed_incidents
            if (factor := self._factor(review, reference)) is not None
        )
        previously_applied = set(applied_review_versions)
        factors = tuple(
            {
                **factor,
                "already_learned": factor["review_version"] in previously_applied,
                "applied_to_baseline": factor["review_version"] not in previously_applied,
            }
            for factor in factors
        )
        new_factors = tuple(item for item in factors if item["applied_to_baseline"])
        total_weight = sum(item["weight"] for item in new_factors)
        signed_weight = sum(item["signed_weight"] for item in new_factors)
        raw_adjustment = (
            self.maximum_adjustment * signed_weight / (self.stabilizer + total_weight)
            if total_weight
            else 0.0
        )
        default_threshold = verification.decision_threshold
        base_threshold = (
            min(self.maximum, max(self.minimum, learned_baseline))
            if learned_baseline is not None
            else default_threshold
        )
        final_threshold = min(self.maximum, max(self.minimum, base_threshold + raw_adjustment))
        adjustment = final_threshold - base_threshold
        baseline_verified = (
            verification.fused_probability >= base_threshold
            or verification.override_source is not None
        )
        adaptive_verified = (
            verification.fused_probability >= final_threshold
            or verification.override_source is not None
        )
        evidence = list(verification.evidence)
        if new_factors and adjustment:
            evidence.append(
                f"adaptive threshold {base_threshold:.4f} -> {final_threshold:.4f} "
                f"from {len(new_factors)} newly learned review(s)"
            )
        elif new_factors:
            evidence.append(
                f"learned baseline remained {base_threshold:.4f}; "
                f"{len(new_factors)} new review(s) had no directional correction"
            )
        elif factors:
            evidence.append(
                f"reused learned baseline {base_threshold:.4f}; matching review versions were "
                "already incorporated"
            )
        else:
            evidence.append(
                f"learned threshold remained at baseline {base_threshold:.4f}; "
                "no directional reviewed memory applied"
            )
        learned_versions = tuple(
            sorted(previously_applied | {item["review_version"] for item in new_factors})
        )
        return replace(
            verification,
            verified=adaptive_verified or verification.forced_accept,
            evidence=tuple(evidence),
            decision_threshold=round(final_threshold, 4),
            base_decision_threshold=round(base_threshold, 4),
            threshold_adjustment=round(adjustment, 4),
            threshold_minimum=self.minimum,
            threshold_maximum=self.maximum,
            threshold_stabilizer=self.stabilizer,
            threshold_maximum_adjustment=self.maximum_adjustment,
            threshold_factors=factors,
            baseline_verified=baseline_verified,
            adaptive_verified=adaptive_verified,
            default_decision_threshold=round(default_threshold, 4),
            threshold_profile_updated=bool(new_factors),
            threshold_new_review_count=len(new_factors),
            threshold_applied_review_versions=learned_versions,
        )

    def _factor(self, review: dict, reference: datetime) -> dict | None:
        direction, effect = self._direction(review)
        similarity = float(review.get("influence_weight", review.get("similarity", 0)))
        if not 0 <= similarity <= 1:
            return None
        reviewed_at = self._reviewed_at(review.get("reviewed_at"))
        age_days = max(0.0, (reference - reviewed_at).total_seconds() / 86_400)
        recency = pow(2, -age_days / self.recency_half_life_days)
        weight = similarity * recency
        return {
            "incident_id": str(review.get("incident_id", "")),
            "review_version": (
                f"{review.get('incident_id', '')}@{review.get('reviewed_at', 'unversioned')}"
            ),
            "effect": effect,
            "direction": direction,
            "similarity": round(similarity, 4),
            "recency": round(recency, 4),
            "age_days": round(age_days, 2),
            "weight": round(weight, 4),
            "signed_weight": round(weight * direction, 4),
            "reviewed_severity": str(review.get("reviewed_severity", "")),
            "response_action": str(review.get("response_action", "")),
            "reason": str(review.get("reason", "")),
        }

    def _direction(self, review: dict) -> tuple[int, str]:
        if review.get("false_alarm") is True:
            return 1, "raise_false_alarm"
        original = review.get("original_decision")
        if not isinstance(original, dict):
            return 0, "unchanged"
        reviewed_severity = self.SEVERITY_RANK.get(str(review.get("reviewed_severity")))
        original_severity = self.SEVERITY_RANK.get(str(original.get("severity")))
        reviewed_action = self.ACTION_RANK.get(str(review.get("response_action")))
        original_action = self.ACTION_RANK.get(str(original.get("response_action")))
        severity_delta = (
            reviewed_severity - original_severity
            if reviewed_severity is not None and original_severity is not None
            else 0
        )
        action_delta = (
            reviewed_action - original_action
            if reviewed_action is not None and original_action is not None
            else 0
        )
        corrections = {delta for delta in (severity_delta, action_delta) if delta != 0}
        if any(delta < 0 for delta in corrections) and any(delta > 0 for delta in corrections):
            return 0, "conflicting_correction"
        if any(delta < 0 for delta in corrections):
            return 1, "raise_overestimated"
        if any(delta > 0 for delta in corrections):
            return -1, "lower_underestimated"
        return 0, "unchanged"

    @staticmethod
    def _reviewed_at(value: object) -> datetime:
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value)
                return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
            except ValueError:
                pass
        return datetime.now(UTC)
