import copy
import uuid

from sqlalchemy.orm import Session

from . import playback
from .models import AnomalyEvent, ProcessData, VariableThreshold
from .rules import compute_score, grade_from_score

_last_processed = {}


def _open_event(db: Session, scenario_id: int, process_name: str):
    return (
        db.query(AnomalyEvent)
        .filter(
            AnomalyEvent.scenario_id == scenario_id,
            AnomalyEvent.process_name == process_name,
            AnomalyEvent.status != "조치완료",
        )
        .order_by(AnomalyEvent.detected_at.desc())
        .first()
    )


def run_detection(db: Session):
    scenario_id = playback.active_scenario_id()
    if scenario_id is None:
        return

    current_time = playback.current_scenario_time()
    if current_time is None:
        return

    last_processed = _last_processed.get(scenario_id)

    query = db.query(ProcessData).filter(
        ProcessData.scenario_id == scenario_id,
        ProcessData.timestamp <= current_time,
    )
    if last_processed is not None:
        query = query.filter(ProcessData.timestamp > last_processed)
    rows = query.order_by(ProcessData.timestamp).all()

    if not rows:
        return

    thresholds = {t.variable_name: t for t in db.query(VariableThreshold).all()}

    for row in rows:
        threshold = thresholds.get(row.variable_name)
        if threshold is None:
            continue
        if not threshold.check_upper and row.value > threshold.upper_bound:
            continue

        score = compute_score(row.value, threshold.golden_value, threshold.lower_bound, threshold.upper_bound)
        if score <= 0:
            continue

        event = _open_event(db, scenario_id, row.process_name)
        if event is None:
            event = AnomalyEvent(
                id=uuid.uuid4().hex,
                scenario_id=scenario_id,
                process_name=row.process_name,
                detected_at=row.timestamp,
                last_updated_at=row.timestamp,
                duration_minutes=0,
                severity_grade=grade_from_score(score),
                anomaly_score=score,
                status="미확인",
                variables=[{"variable_name": row.variable_name, "value": row.value, "score": score}],
            )
            db.add(event)
            db.flush()
        else:
            variables = copy.deepcopy(event.variables)
            for v in variables:
                if v["variable_name"] == row.variable_name:
                    v["value"] = row.value
                    v["score"] = score
                    break
            else:
                variables.append({"variable_name": row.variable_name, "value": row.value, "score": score})

            event.variables = variables
            event.anomaly_score = max(event.anomaly_score, score)
            event.severity_grade = grade_from_score(event.anomaly_score)
            event.last_updated_at = row.timestamp
            event.duration_minutes = (row.timestamp - event.detected_at).total_seconds() / 60

    _last_processed[scenario_id] = rows[-1].timestamp
    db.commit()
