import json

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .cause_analysis import analyze_causes, direction_of, match_case
from .llm import generate_recommended_actions
from .models import AnomalyEvent, RecommendedAction, RecommendedActionSummary, VariableThreshold
from .quality_prediction import _defect_probability, _total_score, defect_probability_excluding

MAX_ACTIONS = 3

PRIORITY_LEVELS = ["즉시", "30분 이내", "순차 처리"]
PRIORITY_ORDER = {p: i for i, p in enumerate(PRIORITY_LEVELS)}


def _representative_variable(cause: dict, contributing: list[dict]) -> dict | None:
    contribution_by_name = {v["variable_name"]: v for v in contributing}
    candidates = [contribution_by_name[name] for name in cause["related_variables"] if name in contribution_by_name]
    if not candidates:
        return None
    return max(candidates, key=lambda v: v["contribution_pct"])


def _fallback_description(case) -> str:
    if case is not None:
        return f"유사 상황({case.situation})에서 이 방식으로 대응한 결과 '{case.result}'였습니다."
    return "유사 조치 사례가 아직 없어 추가 확인이 필요합니다."


def _generate_descriptions(entries: list[dict]) -> list[dict]:
    if entries:
        raw = generate_recommended_actions(entries)
        if raw is not None:
            processed = _postprocess_ai_actions(raw, entries)
            if processed is not None:
                return processed

    return [
        {"cause_index": i, "priority": PRIORITY_LEVELS[min(i, len(PRIORITY_LEVELS) - 1)], "description": e["fallback_description"]}
        for i, e in enumerate(entries)
    ]


def _postprocess_ai_actions(raw_actions: list, entries: list[dict]):
    results = []
    used_indices = set()
    used_priorities = set()

    for item in raw_actions[: len(entries)]:
        idx = item.get("cause_index")
        priority = item.get("priority")
        description = item.get("description")
        if not isinstance(idx, int) or idx not in range(len(entries)) or idx in used_indices:
            continue
        if priority not in PRIORITY_LEVELS or priority in used_priorities:
            continue
        if not description:
            continue

        results.append({"cause_index": idx, "priority": priority, "description": description})
        used_indices.add(idx)
        used_priorities.add(priority)

    if len(results) != len(entries):
        return None

    return results


def recommend_actions(db: Session, anomaly_event_id: str):
    try:
        return _recommend_actions_once(db, anomaly_event_id)
    except IntegrityError:
        db.rollback()
        return _recommend_actions_once(db, anomaly_event_id)


def _recommend_actions_once(db: Session, anomaly_event_id: str):
    event = db.query(AnomalyEvent).filter(AnomalyEvent.id == anomaly_event_id).first()
    if event is None:
        return []

    all_variables, causes = analyze_causes(db, anomaly_event_id)
    contributing = [v for v in all_variables if v["contribution_pct"] > 0]
    signature = json.dumps(
        [{"cause_name": c["cause_name"], "related_variables": c["related_variables"]} for c in causes],
        ensure_ascii=False,
    )

    thresholds = {t.variable_name: t for t in db.query(VariableThreshold).all()}
    current_pct = _defect_probability(_total_score(event), event.duration_minutes)

    entries = []
    context = []
    seen_variables = set()
    for cause in causes[:MAX_ACTIONS]:
        rep_var = _representative_variable(cause, contributing)
        if rep_var is None:
            continue
        if rep_var["variable_name"] in seen_variables:
            continue
        seen_variables.add(rep_var["variable_name"])
        threshold = thresholds.get(rep_var["variable_name"])
        if threshold is None:
            continue

        direction = direction_of(rep_var["current_value"], threshold)
        case = match_case(db, rep_var["variable_name"], direction)

        entries.append(
            {
                "cause_name": cause["cause_name"],
                "likelihood_pct": cause["likelihood_pct"],
                "response": case.response if case is not None else None,
                "result": case.result if case is not None else None,
                "fallback_description": _fallback_description(case),
            }
        )
        context.append(
            {
                "cause": cause,
                "rep_var": rep_var,
                "threshold": threshold,
                "case": case,
            }
        )

    summary = (
        db.query(RecommendedActionSummary)
        .filter(RecommendedActionSummary.anomaly_event_id == anomaly_event_id)
        .first()
    )
    if summary is not None and summary.variable_signature == signature:
        descriptions = summary.actions
    else:
        descriptions = _generate_descriptions(entries)
        if summary is None:
            summary = RecommendedActionSummary(
                anomaly_event_id=anomaly_event_id, variable_signature=signature, actions=descriptions
            )
            db.add(summary)
        else:
            summary.variable_signature = signature
            summary.actions = descriptions

    db.query(RecommendedAction).filter(RecommendedAction.anomaly_event_id == anomaly_event_id).delete()

    descriptions_sorted = sorted(descriptions, key=lambda d: PRIORITY_ORDER[d["priority"]])

    results = []
    for rank, desc in enumerate(descriptions_sorted, start=1):
        ctx = context[desc["cause_index"]]
        cause = ctx["cause"]
        rep_var = ctx["rep_var"]
        threshold = ctx["threshold"]
        case = ctx["case"]

        action_name = case.response if case is not None else f"{cause['cause_name']} 관련 대응 방법 검토 필요"

        action = RecommendedAction(
            anomaly_event_id=anomaly_event_id,
            rank=rank,
            priority=desc["priority"],
            action_name=action_name,
            description=desc["description"],
            score=cause["likelihood_pct"],
        )
        action.variable_name = rep_var["variable_name"]
        action.current_value = rep_var["current_value"]
        action.target_value = threshold.golden_value
        action.unit = threshold.unit
        action.expected_effect = _expected_effect(
            current_pct, defect_probability_excluding(event, rep_var["variable_name"])
        )

        db.add(action)
        results.append(action)

    db.commit()
    return results


def _expected_effect(current_pct: float, after_pct: float) -> str:
    return f"불량 가능성 {current_pct:.1f}% → {after_pct:.1f}%"
