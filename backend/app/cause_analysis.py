import json

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .korean import subject_particle
from .llm import generate_holistic_causes
from .models import AnomalyEvent, Case, CauseSummary, ProcessData, VariableThreshold

MAX_AI_CAUSES = 3


def direction_of(value: float, threshold: VariableThreshold) -> str:
    return "초과" if value > threshold.golden_upper else "미만"


def match_case(db: Session, variable_name: str, direction: str):
    return (
        db.query(Case)
        .filter(Case.category == variable_name, Case.direction == direction)
        .order_by(Case.id)
        .first()
    )


def compute_variable_causes(db: Session, event: AnomalyEvent) -> list[dict]:
    thresholds = {t.variable_name: t for t in db.query(VariableThreshold).all()}
    variables = sorted(event.variables, key=lambda v: v["score"], reverse=True)
    total_score = sum(v["score"] for v in variables)

    results = []
    seen = set()
    for rank, v in enumerate(variables, start=1):
        contribution_pct = (v["score"] / total_score * 100) if total_score > 0 else 0
        threshold = thresholds.get(v["variable_name"])
        direction = direction_of(v["value"], threshold) if threshold else "초과"
        case = match_case(db, v["variable_name"], direction)
        results.append(
            {
                "variable_name": v["variable_name"],
                "rank": rank,
                "contribution_pct": contribution_pct,
                "direction": direction,
                "case": case,
                "current_value": v["value"],
                "threshold": threshold,
            }
        )
        seen.add(v["variable_name"])

    for name, threshold in thresholds.items():
        if name in seen:
            continue
        latest = (
            db.query(ProcessData)
            .filter(
                ProcessData.scenario_id == event.scenario_id,
                ProcessData.process_name == event.process_name,
                ProcessData.variable_name == name,
                ProcessData.timestamp <= event.last_updated_at,
            )
            .order_by(ProcessData.timestamp.desc())
            .first()
        )
        results.append(
            {
                "variable_name": name,
                "rank": None,
                "contribution_pct": 0.0,
                "direction": None,
                "case": None,
                "current_value": latest.value if latest else (threshold.golden_lower + threshold.golden_upper) / 2,
                "threshold": threshold,
            }
        )

    results.sort(key=lambda r: r["contribution_pct"], reverse=True)
    return results


def _cause_name_rule_based(variable_name: str, case) -> str:
    if case is not None:
        return case.possible_causes[0]["name"]
    return f"{variable_name} 이상 (유사 사례 없음)"


def _describe_rule_based(rank: int, variable_name: str, contribution_pct: float, case) -> tuple[str, str]:
    verdict = "가장 유력한 원인" if rank == 1 else "추가로 영향을 준 원인"
    cause_name = _cause_name_rule_based(variable_name, case)

    if case is not None:
        text = (
            f"{cause_name}{subject_particle(cause_name)} {verdict}으로 분석됩니다(기여도 {contribution_pct:.1f}%). "
            f"{variable_name} 변수의 이상 정도와 유사 사례({case.situation})를 종합적으로 분석한 결과입니다."
        )
    else:
        text = (
            f"{variable_name} 변수의 이상 정도를 근거로 {verdict}으로 분석되며, 기여도는 {contribution_pct:.1f}%입니다. "
            f"명확히 일치하는 과거 사례는 아직 없어 추가 확인이 필요합니다."
        )
    return cause_name, text


def _fallback_causes(contributing: list[dict]) -> list[dict]:
    results = []
    for rank, vc in enumerate(contributing[:MAX_AI_CAUSES], start=1):
        cause_name, description = _describe_rule_based(rank, vc["variable_name"], vc["contribution_pct"], vc["case"])
        results.append(
            {
                "rank": rank,
                "cause_name": cause_name,
                "description": description,
                "likelihood_pct": vc["contribution_pct"],
                "related_variables": [vc["variable_name"]],
            }
        )
    return results


def _postprocess_ai_causes(raw_causes: list, contributing: list[dict]):
    contribution_by_name = {vc["variable_name"]: vc["contribution_pct"] for vc in contributing}
    valid_names = set(contribution_by_name)

    considered = raw_causes[:MAX_AI_CAUSES]
    results = []
    for item in considered:
        cause_name = item.get("cause_name")
        description = item.get("description")
        related = [name for name in item.get("related_variables", []) if name in valid_names]
        if not cause_name or not description or not related:
            continue

        link_justification = (item.get("link_justification") or "").strip()
        if len(related) > 1 and len(link_justification) < 8:
            continue

        likelihood_pct = item.get("likelihood_pct")
        if not isinstance(likelihood_pct, (int, float)):
            likelihood_pct = sum(contribution_by_name[name] for name in related)
        likelihood_pct = max(0.0, min(100.0, likelihood_pct))

        results.append(
            {
                "cause_name": cause_name,
                "description": description,
                "related_variables": related,
                "likelihood_pct": likelihood_pct,
            }
        )

    if len(results) < 2 or len(results) != len(considered):
        return None

    results.sort(key=lambda c: c["likelihood_pct"], reverse=True)
    for rank, c in enumerate(results, start=1):
        c["rank"] = rank
    return results


def _generate_causes(contributing: list[dict]) -> list[dict]:
    if contributing:
        for _ in range(2):
            raw = generate_holistic_causes(contributing)
            if raw is None:
                continue
            processed = _postprocess_ai_causes(raw, contributing)
            if processed is not None:
                return processed
    return _fallback_causes(contributing)


def _signature(contributing: list[dict]) -> str:
    return json.dumps([vc["variable_name"] for vc in contributing], ensure_ascii=False)


def analyze_causes(db: Session, anomaly_event_id: str):
    try:
        return _analyze_causes_once(db, anomaly_event_id)
    except IntegrityError:
        db.rollback()
        return _analyze_causes_once(db, anomaly_event_id)


def _analyze_causes_once(db: Session, anomaly_event_id: str):
    event = db.query(AnomalyEvent).filter(AnomalyEvent.id == anomaly_event_id).first()
    if event is None:
        return [], []

    all_variables = compute_variable_causes(db, event)
    contributing = [v for v in all_variables if v["contribution_pct"] > 0]
    signature = _signature(contributing)

    summary = db.query(CauseSummary).filter(CauseSummary.anomaly_event_id == anomaly_event_id).first()
    if summary is not None and summary.variable_signature == signature:
        return all_variables, summary.causes

    causes = _generate_causes(contributing)
    if summary is None:
        summary = CauseSummary(anomaly_event_id=anomaly_event_id, variable_signature=signature, causes=causes)
        db.add(summary)
    else:
        summary.variable_signature = signature
        summary.causes = causes
    db.commit()

    return all_variables, causes
