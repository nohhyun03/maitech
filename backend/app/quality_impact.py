from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .cause_analysis import _signature, analyze_causes
from .llm import generate_quality_impacts
from .models import QualityImpactSummary

MAX_IMPACTS = 3


def _fallback_impacts(contributing: list[dict]) -> list[dict]:
    tag_weights = {}
    tag_contributors = {}
    for v in contributing:
        if v["case"] is None:
            continue
        for tag in v["case"].defect_tags:
            tag_weights[tag] = tag_weights.get(tag, 0.0) + v["contribution_pct"]
            tag_contributors.setdefault(tag, []).append((v["variable_name"], v["contribution_pct"]))

    top_tags = sorted(tag_weights.items(), key=lambda item: item[1], reverse=True)[:MAX_IMPACTS]

    impacts = []
    for tag, weight in top_tags:
        contributors = sorted(tag_contributors[tag], key=lambda item: item[1], reverse=True)
        variable_list = ", ".join(f"{name}({pct:.1f}%)" for name, pct in contributors)
        estimated_pct = min(100.0, weight)
        impacts.append(
            {
                "label": tag,
                "description": f"{variable_list} 이상이 복합적으로 작용해 {tag} 가능성이 약 {estimated_pct:.0f}% 수준으로 예상됩니다.",
                "related_variables": [name for name, _ in contributors],
                "likelihood_pct": estimated_pct,
            }
        )
    return impacts


def _allowed_labels(contributing: list[dict]) -> set:
    labels = set()
    for v in contributing:
        if v["case"] is not None:
            labels.update(v["case"].defect_tags)
    return labels


def _postprocess_ai_impacts(raw_impacts: list, contributing: list[dict]):
    valid_names = {v["variable_name"] for v in contributing}
    allowed_labels = _allowed_labels(contributing)

    considered = raw_impacts[: min(MAX_IMPACTS, len(allowed_labels))]
    results = []
    used_labels = set()
    for item in considered:
        label = item.get("label")
        description = item.get("description")
        related = [name for name in item.get("related_variables", []) if name in valid_names]
        if not label or not description or not related:
            continue
        if label not in allowed_labels or label in used_labels:
            continue
        used_labels.add(label)

        likelihood_pct = item.get("likelihood_pct")
        if not isinstance(likelihood_pct, (int, float)):
            continue
        likelihood_pct = max(0.0, min(100.0, likelihood_pct))

        results.append(
            {
                "label": label,
                "description": description,
                "related_variables": related,
                "likelihood_pct": likelihood_pct,
            }
        )

    if len(results) < min(2, len(allowed_labels)) or len(results) != len(considered):
        return None

    results.sort(key=lambda i: i["likelihood_pct"], reverse=True)
    return results


def _generate_impacts(contributing: list[dict]) -> list[dict]:
    if contributing:
        for _ in range(2):
            raw = generate_quality_impacts(contributing)
            if raw is None:
                continue
            processed = _postprocess_ai_impacts(raw, contributing)
            if processed is not None:
                return processed
    return _fallback_impacts(contributing)


def predict_quality_impact(db: Session, anomaly_event_id: str):
    try:
        return _predict_quality_impact_once(db, anomaly_event_id)
    except IntegrityError:
        db.rollback()
        return _predict_quality_impact_once(db, anomaly_event_id)


def _predict_quality_impact_once(db: Session, anomaly_event_id: str):
    all_variables, _ = analyze_causes(db, anomaly_event_id)
    contributing = [v for v in all_variables if v["contribution_pct"] > 0]
    signature = _signature(contributing)

    summary = (
        db.query(QualityImpactSummary)
        .filter(QualityImpactSummary.anomaly_event_id == anomaly_event_id)
        .first()
    )
    if summary is not None and summary.variable_signature == signature:
        return summary.impacts

    impacts = _generate_impacts(contributing)
    if summary is None:
        summary = QualityImpactSummary(
            anomaly_event_id=anomaly_event_id, variable_signature=signature, impacts=impacts
        )
        db.add(summary)
    else:
        summary.variable_signature = signature
        summary.impacts = impacts
    db.commit()

    return impacts
