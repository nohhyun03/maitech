from sqlalchemy.orm import Session

from .korean import subject_particle
from .models import AnomalyEvent, Case, CauseAnalysis, VariableThreshold


def direction_of(value: float, threshold: VariableThreshold) -> str:
    return "초과" if value > threshold.golden_value else "미만"


def match_case(db: Session, variable_name: str, direction: str):
    return (
        db.query(Case)
        .filter(Case.category == variable_name, Case.direction == direction)
        .order_by(Case.id)
        .first()
    )


BASE_CONFIDENCE = 0.4
SEVERITY_WEIGHT = 0.3
CASE_MATCH_WEIGHT = 0.3
SEVERITY_SCORE_CAP = 2.0


def _cause_name(variable_name: str, case) -> str:
    if case is not None:
        return case.cause
    return f"{variable_name} 이상 (유사 사례 없음)"


def _confidence_factor(score: float, case) -> float:
    severity_component = min(score, SEVERITY_SCORE_CAP) / SEVERITY_SCORE_CAP
    case_component = 1.0 if case is not None else 0.0
    return BASE_CONFIDENCE + SEVERITY_WEIGHT * severity_component + CASE_MATCH_WEIGHT * case_component


def _likelihood_pct(contribution_pct: float, score: float, case) -> float:
    return min(100.0, contribution_pct * _confidence_factor(score, case))


def _describe(rank: int, variable_name: str, contribution_pct: float, likelihood_pct: float, case) -> str:
    verdict = "가장 유력한 원인" if rank == 1 else "추가로 영향을 준 원인"
    cause_name = _cause_name(variable_name, case)

    if case is not None:
        text = (
            f"{cause_name}{subject_particle(cause_name)} {verdict}으로 분석됩니다(가능성 {likelihood_pct:.1f}%). "
            f"{variable_name} 변수의 이상 정도와 유사 사례({case.situation})를 종합적으로 분석한 결과입니다. "
            f"참고로 이 변수의 이상 점수 기여도는 {contribution_pct:.1f}%입니다."
        )
    else:
        text = (
            f"{variable_name} 변수의 이상 정도를 근거로 {verdict}으로 분석되며, 가능성은 {likelihood_pct:.1f}%로 추정됩니다. "
            f"명확히 일치하는 과거 사례는 아직 없어 추가 확인이 필요합니다. (이상 점수 기여도 {contribution_pct:.1f}%)"
        )
    return text


def analyze_causes(db: Session, anomaly_event_id: str):
    event = db.query(AnomalyEvent).filter(AnomalyEvent.id == anomaly_event_id).first()
    if event is None:
        return []

    db.query(CauseAnalysis).filter(CauseAnalysis.anomaly_event_id == anomaly_event_id).delete()

    thresholds = {t.variable_name: t for t in db.query(VariableThreshold).all()}
    variables = sorted(event.variables, key=lambda v: v["score"], reverse=True)
    total_score = sum(v["score"] for v in variables)

    results = []
    for rank, v in enumerate(variables, start=1):
        contribution_pct = (v["score"] / total_score * 100) if total_score > 0 else 0
        threshold = thresholds.get(v["variable_name"])
        direction = direction_of(v["value"], threshold) if threshold else "초과"
        case = match_case(db, v["variable_name"], direction)
        likelihood_pct = _likelihood_pct(contribution_pct, v["score"], case)
        description = _describe(rank, v["variable_name"], contribution_pct, likelihood_pct, case)

        analysis = CauseAnalysis(
            anomaly_event_id=anomaly_event_id,
            rank=rank,
            contribution_pct=contribution_pct,
            cause_name=_cause_name(v["variable_name"], case),
            description=description,
            matched_case_id=case.id if case else None,
        )
        analysis.variable_name = v["variable_name"]
        analysis.likelihood_pct = likelihood_pct

        db.add(analysis)
        results.append(analysis)

    db.commit()
    return results
