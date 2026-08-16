from sqlalchemy.orm import Session

from .models import AnomalyEvent, QualityPrediction

SCORE_WEIGHT = 6
DURATION_WEIGHT = 1.5


def _total_score(event: AnomalyEvent, exclude_variable: str = None) -> float:
    return sum(v["score"] for v in event.variables if v["variable_name"] != exclude_variable)


def _defect_probability(total_score: float, duration_minutes: float) -> float:
    raw = total_score * SCORE_WEIGHT + duration_minutes * DURATION_WEIGHT
    return max(0.0, min(100.0, raw))


def defect_probability_excluding(event: AnomalyEvent, variable_name: str) -> float:
    return _defect_probability(_total_score(event, exclude_variable=variable_name), event.duration_minutes)


def _impact_label(defect_probability: float) -> str:
    if defect_probability >= 50:
        return "불량 위험 높음"
    if defect_probability >= 20:
        return "품질 저하 우려"
    return "정상 품질 유지 예상"


def _describe(impact_label: str, defect_probability: float, duration_minutes: float) -> str:
    return (
        f"현재 이상 상태가 {duration_minutes:.1f}분간 지속되어 불량 가능성이 {defect_probability:.1f}%로 예측됩니다. "
        f"이 추세가 계속되면 '{impact_label}' 상태로 이어질 수 있습니다."
    )


def predict_quality(db: Session, anomaly_event_id: str):
    event = db.query(AnomalyEvent).filter(AnomalyEvent.id == anomaly_event_id).first()
    if event is None:
        return None

    db.query(QualityPrediction).filter(QualityPrediction.anomaly_event_id == anomaly_event_id).delete()

    defect_probability = _defect_probability(_total_score(event), event.duration_minutes)
    impact_label = _impact_label(defect_probability)
    description = _describe(impact_label, defect_probability, event.duration_minutes)

    prediction = QualityPrediction(
        anomaly_event_id=anomaly_event_id,
        impact_label=impact_label,
        description=description,
        confidence_pct=defect_probability,
    )
    db.add(prediction)
    db.commit()
    return prediction
