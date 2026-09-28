from __future__ import annotations

import math
from dataclasses import dataclass
from typing import ClassVar

from .models import IncidentContext, Severity


@dataclass(frozen=True)
class MemoryReconciliation:
    """Similarity-weighted interpolation from an AI draft to a human-reviewed outcome."""

    incident_id: str
    similarity: float
    current_weight: float
    base_severity: Severity
    base_action: str
    reviewed_severity: Severity
    reviewed_action: str
    final_severity: Severity
    final_action: str
    severity_score: float
    action_score: float
    reviewed_severity_floor: Severity
    effect: str

    def audit(self) -> dict[str, object]:
        return {
            "applied": True,
            "incident_ids": [self.incident_id],
            "effect": self.effect,
            "explanation": (
                f"Similarity-weighted reconciliation used {self.similarity:.0%} reviewed memory "
                f"and {self.current_weight:.0%} current AI draft; final outcome is "
                f"{self.final_severity.value}/{self.final_action}."
            ),
            "weight": self.similarity,
            "current_weight": self.current_weight,
            "base_severity": self.base_severity.value,
            "base_action": self.base_action,
            "reviewed_severity": self.reviewed_severity.value,
            "reviewed_action": self.reviewed_action,
            "severity_score": self.severity_score,
            "action_score": self.action_score,
            "reviewed_severity_floor": self.reviewed_severity_floor.value,
            "method": "similarity_weighted_human_review_v1",
        }


class ReviewedMemoryDecisionModel:
    """Apply the closest human review in direct proportion to evidence similarity.

    At similarity 1.0 the reviewed outcome is reproduced exactly. Below 1.0, the
    current AI draft retains the complementary weight (1 - similarity).
    """

    SEVERITIES: ClassVar[tuple[Severity, ...]] = (
        Severity.LOW,
        Severity.MEDIUM,
        Severity.HIGH,
        Severity.CRITICAL,
    )
    ACTIONS: ClassVar[tuple[str, ...]] = ("none", "message", "call")

    def reconcile(
        self,
        base_severity: Severity,
        base_action: str,
        context: IncidentContext,
    ) -> MemoryReconciliation | None:
        candidates = []
        for review in context.reviewed_incidents:
            try:
                similarity = min(
                    1.0,
                    max(0.0, float(review.get("influence_weight", review.get("similarity", 0)))),
                )
                reviewed_severity = (
                    Severity.LOW
                    if review.get("false_alarm")
                    else Severity(str(review.get("reviewed_severity")))
                )
                reviewed_action = (
                    "none" if review.get("false_alarm") else str(review.get("response_action"))
                )
                if reviewed_action not in self.ACTIONS or not review.get("incident_id"):
                    continue
            except (TypeError, ValueError):
                continue
            candidates.append(
                (similarity, str(review["incident_id"]), reviewed_severity, reviewed_action)
            )
        if not candidates:
            return None

        similarity, incident_id, reviewed_severity, reviewed_action = max(
            candidates, key=lambda item: item[0]
        )
        base_action = base_action if base_action in self.ACTIONS else "none"
        current_weight = 1.0 - similarity
        severity_score = current_weight * self.SEVERITIES.index(base_severity) + similarity * (
            self.SEVERITIES.index(reviewed_severity)
        )
        action_score = current_weight * self.ACTIONS.index(base_action) + similarity * (
            self.ACTIONS.index(reviewed_action)
        )
        reviewed_severity_floor_rank = math.floor(
            similarity * self.SEVERITIES.index(reviewed_severity)
        )
        final_severity_rank = self._round_rank(severity_score, len(self.SEVERITIES))
        if self.SEVERITIES.index(reviewed_severity) > self.SEVERITIES.index(base_severity):
            final_severity_rank = max(final_severity_rank, reviewed_severity_floor_rank)
        final_severity = self.SEVERITIES[final_severity_rank]
        final_action = self.ACTIONS[self._round_rank(action_score, len(self.ACTIONS))]
        base_total = self.SEVERITIES.index(base_severity) + self.ACTIONS.index(base_action)
        final_total = self.SEVERITIES.index(final_severity) + self.ACTIONS.index(final_action)
        effect = (
            "raised"
            if final_total > base_total
            else "lowered"
            if final_total < base_total
            else "confirmed"
        )
        return MemoryReconciliation(
            incident_id=incident_id,
            similarity=round(similarity, 4),
            current_weight=round(current_weight, 4),
            base_severity=base_severity,
            base_action=base_action,
            reviewed_severity=reviewed_severity,
            reviewed_action=reviewed_action,
            final_severity=final_severity,
            final_action=final_action,
            severity_score=round(severity_score, 4),
            action_score=round(action_score, 4),
            reviewed_severity_floor=self.SEVERITIES[reviewed_severity_floor_rank],
            effect=effect,
        )

    @staticmethod
    def _round_rank(value: float, size: int) -> int:
        return min(size - 1, max(0, math.floor(value + 0.5)))
