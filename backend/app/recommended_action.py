from sqlalchemy.orm import Session

from .cause_analysis import analyze_causes, direction_of, match_case
from .models import AnomalyEvent, RecommendedAction, VariableThreshold
from .quality_prediction import _defect_probability, _total_score, defect_probability_excluding

MAX_ACTIONS = 3

URGENCY_BY_RANK = {1: "즉시", 2: "30분 이내", 3: "순차 처리"}


def _describe(variable_name: str, case) -> str:
    if case is not None:
        return f"유사 상황({case.situation})에서 이 방식으로 대응한 결과 '{case.result}'였습니다."
    return f"{variable_name} 이상에 대한 유사 조치 사례가 아직 없어 구체적인 조정 방법은 추가 확인이 필요합니다."


def _expected_effect(current_pct: float, after_pct: float) -> str:
    return f"불량 가능성 {current_pct:.1f}% → {after_pct:.1f}%"


def recommend_actions(db: Session, anomaly_event_id: str):
    event = db.query(AnomalyEvent).filter(AnomalyEvent.id == anomaly_event_id).first()
    if event is None:
        return []

    db.query(RecommendedAction).filter(RecommendedAction.anomaly_event_id == anomaly_event_id).delete()

    causes = analyze_causes(db, anomaly_event_id)
    ranked = [c for c in causes if c.contribution_pct > 0][:MAX_ACTIONS]

    thresholds = {t.variable_name: t for t in db.query(VariableThreshold).all()}
    current_pct = _defect_probability(_total_score(event), event.duration_minutes)

    results = []
    for rank, cause in enumerate(ranked, start=1):
        threshold = thresholds.get(cause.variable_name)
        if threshold is None:
            continue

        target = threshold.golden_value
        variable_value = next(
            (v["value"] for v in event.variables if v["variable_name"] == cause.variable_name),
            target,
        )
        direction = direction_of(variable_value, threshold)
        case = match_case(db, cause.variable_name, direction)

        action_name = case.response if case is not None else f"{cause.variable_name} 이상 대응 방법 검토 필요"

        action = RecommendedAction(
            anomaly_event_id=anomaly_event_id,
            rank=rank,
            priority=URGENCY_BY_RANK.get(rank, "순차 처리"),
            action_name=action_name,
            description=_describe(cause.variable_name, case),
            score=cause.contribution_pct,
        )
        action.variable_name = cause.variable_name
        action.current_value = variable_value
        action.target_value = target
        action.unit = threshold.unit
        action.expected_effect = _expected_effect(current_pct, defect_probability_excluding(event, cause.variable_name))

        db.add(action)
        results.append(action)

    db.commit()
    return results
