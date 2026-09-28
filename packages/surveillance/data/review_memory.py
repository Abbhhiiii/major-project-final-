from dataclasses import replace
from datetime import UTC, datetime

from sqlalchemy import select

from .models import AgentAuditRow, IncidentReviewRow


def _match(current: float, previous: float, scale: float = 1.0) -> float:
    return round(max(0.0, 1.0 - min(1.0, abs(current - previous) / scale)), 4)


def _timeline_stats(timeline, sensor_type: str) -> dict[str, float] | None:
    values: list[float] = []
    for sample in timeline or ():
        readings = sample.get("readings", []) if isinstance(sample, dict) else sample.readings
        for reading in readings:
            kind = reading.get("sensor_type") if isinstance(reading, dict) else reading.sensor_type
            if kind == sensor_type:
                value = (
                    reading.get("probability") if isinstance(reading, dict) else reading.probability
                )
                values.append(float(value))
                break
    if not values:
        return None
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return {
        "mean": mean,
        "maximum": max(values),
        "variability": variance**0.5,
    }


def _evidence_similarity(detection, scan: dict) -> dict | None:
    """Compare every comparable visual and sensor feature with explicit weights."""

    old_sensors = {item["sensor_type"]: item for item in scan.get("sensor_readings", [])}
    new_sensors = {item.sensor_type: item for item in detection.sensor_readings}
    if set(old_sensors) != set(new_sensors):
        return None

    sensor_mass = 0.7 if new_sensors else 0.0
    visual_weight = (1.0 - sensor_mass) / 2
    features = [
        {
            "key": "visual.confidence",
            "label": "CV confidence",
            "current": detection.confidence,
            "previous": scan["confidence"],
            "match": _match(detection.confidence, scan["confidence"]),
            "weight": visual_weight,
        },
        {
            "key": "visual.impact_score",
            "label": "Visual impact",
            "current": detection.impact_score,
            "previous": scan["impact_score"],
            "match": _match(detection.impact_score, scan["impact_score"]),
            "weight": visual_weight,
        },
    ]
    sensor_matches = []
    per_sensor_weight = sensor_mass / len(new_sensors) if new_sensors else 0.0
    for sensor_type in sorted(new_sensors):
        current = new_sensors[sensor_type]
        previous = old_sensors[sensor_type]
        current_timeline = _timeline_stats(detection.sensor_timeline, sensor_type)
        previous_timeline = _timeline_stats(scan.get("sensor_timeline", []), sensor_type)
        dimensions = [
            (
                "probability",
                "Candidate probability",
                current.probability,
                previous["probability"],
                0.35,
                1.0,
            ),
            (
                "reliability",
                "Candidate reliability",
                current.reliability,
                previous["reliability"],
                0.2,
                1.0,
            ),
            ("freshness", "Candidate freshness", current.age_ms, previous["age_ms"], 0.1, 10_000.0),
        ]
        if current_timeline is not None and previous_timeline is not None:
            dimensions.extend(
                (
                    (
                        "timeline_mean",
                        "Timeline mean",
                        current_timeline["mean"],
                        previous_timeline["mean"],
                        0.15,
                        1.0,
                    ),
                    (
                        "timeline_max",
                        "Timeline maximum",
                        current_timeline["maximum"],
                        previous_timeline["maximum"],
                        0.15,
                        1.0,
                    ),
                    (
                        "timeline_variability",
                        "Timeline variability",
                        current_timeline["variability"],
                        previous_timeline["variability"],
                        0.05,
                        0.5,
                    ),
                )
            )
        else:
            dimensions[0] = (*dimensions[0][:4], 0.5, dimensions[0][5])
            dimensions[1] = (*dimensions[1][:4], 0.3, dimensions[1][5])
            dimensions[2] = (*dimensions[2][:4], 0.2, dimensions[2][5])
        sensor_features = []
        for key, label, current_value, previous_value, share, scale in dimensions:
            feature = {
                "key": f"sensor.{sensor_type}.{key}",
                "label": f"{sensor_type.title()} {label.lower()}",
                "current": current_value,
                "previous": previous_value,
                "match": _match(float(current_value), float(previous_value), scale),
                "weight": per_sensor_weight * share,
            }
            features.append(feature)
            sensor_features.append(feature)
        sensor_matches.append(
            {
                "sensor_type": sensor_type,
                "match": round(
                    sum(item["match"] * item["weight"] for item in sensor_features)
                    / per_sensor_weight,
                    4,
                ),
                "weight": round(per_sensor_weight, 4),
            }
        )

    for feature in features:
        feature["weight"] = round(feature["weight"], 4)
        feature["weighted_match"] = round(feature["match"] * feature["weight"], 4)
    similarity = round(sum(item["weighted_match"] for item in features), 4)
    return {
        "similarity": similarity,
        "influence_weight": similarity,
        "feature_matches": features,
        "sensor_matches": sensor_matches,
        "match_method": "weighted_full_sensor_profile_v1",
    }


class ReviewedContextRepository:
    """Organization-scoped, evidence-matched human corrections augment policy retrieval."""

    def __init__(self, sessions, policies):
        self.sessions = sessions
        self.policies = policies

    def get(self, incident_id, organization_id):
        with self.sessions() as session:
            row = session.get(IncidentReviewRow, incident_id)
            if row is None or row.organization_id != organization_id:
                return None
            return {column.name: getattr(row, column.name) for column in row.__table__.columns}

    def save(self, incident_id, organization_id, reviewer_id, values):
        with self.sessions() as session:
            session.merge(
                IncidentReviewRow(
                    incident_id=incident_id,
                    organization_id=organization_id,
                    reviewer_id=reviewer_id,
                    updated_at=datetime.now(UTC).isoformat(),
                    **values,
                )
            )
            session.commit()
        return self.get(incident_id, organization_id)

    def retrieve(self, detection):
        context = self.policies.retrieve(detection)
        if not detection.organization_id:
            return context
        with self.sessions() as session:
            rows = session.execute(
                select(IncidentReviewRow, AgentAuditRow)
                .join(AgentAuditRow, AgentAuditRow.incident_id == IncidentReviewRow.incident_id)
                .where(IncidentReviewRow.organization_id == detection.organization_id)
            ).all()
            matches = []
            for review, audit in rows:
                scan = audit.retrieval.get("scan_snapshot", {})
                if not scan:
                    continue
                same_location = (
                    detection.location.strip().casefold()
                    == scan.get("location", "").strip().casefold()
                )
                comparison = _evidence_similarity(detection, scan)
                if not same_location or comparison is None or comparison["similarity"] < 0.7:
                    continue
                matches.append(
                    {
                        "incident_id": review.incident_id,
                        **comparison,
                        "reviewed_severity": review.severity,
                        "response_action": review.response_action,
                        "false_alarm": review.false_alarm,
                        "reason": review.reason,
                        "reviewed_at": review.updated_at,
                        "original_decision": audit.decision,
                        "scan": scan,
                        "verification": audit.retrieval.get("verification_snapshot", {}),
                    }
                )
        matches.sort(key=lambda item: (item["similarity"], item["reviewed_at"]), reverse=True)
        return replace(
            context, reviewed_incidents=tuple(matches[:1]), prior_incident_count=len(matches)
        )
