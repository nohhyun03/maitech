import copy
import uuid

from sqlalchemy.orm import Session

from . import playback
from .models import AnomalyEvent, ProcessData, VariableThreshold
from .rules import compute_score, grade_from_score

_last_processed = {}
_candidate_onset = {}

DEBOUNCE_SECONDS = 60


def reset_watermark(scenario_id: int):
    _last_processed.pop(scenario_id, None)
    for key in [k for k in _candidate_onset if k[0] == scenario_id]:
        _candidate_onset.pop(key, None)


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


def _already_completed(db: Session, scenario_id: int, process_name: str, timestamp) -> bool:
    return (
        db.query(AnomalyEvent)
        .filter(
            AnomalyEvent.scenario_id == scenario_id,
            AnomalyEvent.process_name == process_name,
            AnomalyEvent.status == "조치완료",
            AnomalyEvent.detected_at <= timestamp,
            AnomalyEvent.last_updated_at >= timestamp,
        )
        .first()
        is not None
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

        score = compute_score(
            row.value,
            threshold.golden_lower,
            threshold.golden_upper,
            threshold.lower_bound,
            threshold.upper_bound,
            threshold.critical_lower_enabled,
            threshold.critical_upper_enabled,
        )
        candidate_key = (scenario_id, row.process_name, row.variable_name)
        if score <= 0:
            _candidate_onset.pop(candidate_key, None)
            continue

        event = _open_event(db, scenario_id, row.process_name)
        if event is None:
            onset = _candidate_onset.get(candidate_key)
            if onset is None:
                _candidate_onset[candidate_key] = row.timestamp
                continue
            if (row.timestamp - onset).total_seconds() < DEBOUNCE_SECONDS:
                continue
            _candidate_onset.pop(candidate_key, None)

            if _already_completed(db, scenario_id, row.process_name, onset):
                continue
            event = AnomalyEvent(
                id=uuid.uuid4().hex,
                scenario_id=scenario_id,
                process_name=row.process_name,
                detected_at=onset,
                last_updated_at=row.timestamp,
                duration_minutes=(row.timestamp - onset).total_seconds() / 60,
                severity_grade=grade_from_score(score),
                anomaly_score=score,
                status="미확인",
                variables=[{"variable_name": row.variable_name, "value": row.value, "score": score}],
            )
            db.add(event)
            db.flush()
        else:
            _candidate_onset.pop(candidate_key, None)
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
