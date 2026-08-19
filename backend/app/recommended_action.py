import json

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .cause_analysis import analyze_causes, match_case
from .llm import generate_recommended_actions
from .models import AnomalyEvent, RecommendedAction, RecommendedActionSummary, VariableThreshold
from .quality_prediction import _defect_probability, _total_score, defect_probability_excluding

MAX_ACTIONS = 3

PRIORITY_LEVELS = ["우선 시도", "차순위 시도", "최종 시도"]
PRIORITY_ORDER = {p: i for i, p in enumerate(PRIORITY_LEVELS)}


def _cause_names_for(variable_name: str, causes: list[dict]) -> list[str]:
    return [c["cause_name"] for c in causes if variable_name in c["related_variables"]]


def _build_candidates(db: Session, contributing: list[dict], thresholds: dict) -> list[dict]:
    per_variable = []
    for var in sorted(contributing, key=lambda v: v["contribution_pct"], reverse=True):
        threshold = thresholds.get(var["variable_name"])
        if threshold is None:
            continue
        case = match_case(db, var["variable_name"], var["direction"])
        responses = list(case.responses) if case is not None else [None]
        per_variable.append({"var": var, "threshold": threshold, "case": case, "responses": responses})

    candidates = []
    depth = 0
    while len(candidates) < MAX_ACTIONS:
        added = False
        for item in per_variable:
            if len(candidates) >= MAX_ACTIONS:
                break
            if depth >= len(item["responses"]):
                continue
            candidates.append(
                {
                    "var": item["var"],
                    "threshold": item["threshold"],
                    "case": item["case"],
                    "response": item["responses"][depth],
                }
            )
            added = True
        if not added:
            break
        depth += 1
    return candidates


def _fallback_description(case, response) -> str:
    if case is not None and response is not None:
        return f"유사 상황({case.situation})에서 이 방식으로 대응한 결과 '{response['result']}'였습니다."
    return "유사 조치 사례가 아직 없어 추가 확인이 필요합니다."


def _generate_descriptions(entries: list[dict]) -> list[dict]:
    if entries:
        for _ in range(2):
            raw = generate_recommended_actions(entries)
            if raw is None:
                continue
            processed = _postprocess_ai_actions(raw, entries)
            if processed is not None:
                return processed

    return [
        {"action_index": i, "priority": PRIORITY_LEVELS[min(i, len(PRIORITY_LEVELS) - 1)], "description": e["fallback_description"]}
        for i, e in enumerate(entries)
    ]


def _postprocess_ai_actions(raw_actions: list, entries: list[dict]):
    results = []
    used_indices = set()
    used_priorities = set()

    for item in raw_actions[: len(entries)]:
        idx = item.get("action_index")
        priority = item.get("priority")
        description = item.get("description")
        if not isinstance(idx, int) or idx not in range(len(entries)) or idx in used_indices:
            continue
        if priority not in PRIORITY_LEVELS or priority in used_priorities:
            continue
        if not description:
            continue

        results.append({"action_index": idx, "priority": priority, "description": description})
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

    thresholds = {t.variable_name: t for t in db.query(VariableThreshold).all()}
    current_pct = _defect_probability(_total_score(event), event.duration_minutes)

    candidates = _build_candidates(db, contributing, thresholds)

    entries = []
    for candidate in candidates:
        var = candidate["var"]
        response = candidate["response"]
        entries.append(
            {
                "variable_name": var["variable_name"],
                "direction": var["direction"],
                "contribution_pct": var["contribution_pct"],
                "cause_names": _cause_names_for(var["variable_name"], causes),
                "response": response["response"] if response is not None else None,
                "result": response["result"] if response is not None else None,
                "fallback_description": _fallback_description(candidate["case"], response),
            }
        )

    signature = json.dumps(
        {
            "causes": [{"cause_name": c["cause_name"], "related_variables": c["related_variables"]} for c in causes],
            "actions": [{"variable_name": e["variable_name"], "response": e["response"]} for e in entries],
        },
        ensure_ascii=False,
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
        candidate = candidates[desc["action_index"]]
        var = candidate["var"]
        threshold = candidate["threshold"]
        response = candidate["response"]
        cause_names = _cause_names_for(var["variable_name"], causes)

        if response is not None:
            action_name = response["response"]
        elif cause_names:
            action_name = f"{cause_names[0]} 관련 대응 방안 검토"
        else:
            action_name = f"{var['variable_name']} 이상 대응 방안 검토"

        action = RecommendedAction(
            anomaly_event_id=anomaly_event_id,
            rank=rank,
            priority=desc["priority"],
            action_name=action_name,
            description=desc["description"],
            score=var["contribution_pct"],
            variable_name=var["variable_name"],
            current_value=var["current_value"],
            target_value=threshold.golden_value,
            unit=threshold.unit,
            expected_effect=_expected_effect(
                current_pct, defect_probability_excluding(event, var["variable_name"])
            ),
        )

        db.add(action)
        results.append(action)

    db.commit()
    return results


def _expected_effect(current_pct: float, after_pct: float) -> str:
    return f"불량 가능성 {current_pct:.1f}% → {after_pct:.1f}%"
