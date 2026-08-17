from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..action_record import start_action, submit_action_record
from ..cause_analysis import analyze_causes, compute_variable_causes, direction_of
from ..database import get_db
from ..detection import run_detection
from ..models import AnomalyEvent, VariableThreshold
from ..quality_impact import predict_quality_impact
from ..quality_prediction import predict_quality
from ..recommended_action import recommend_actions
from ..rules import grade_from_score
from ..schemas import ActionRecordRequest

router = APIRouter(prefix="/api/anomalies", tags=["anomalies"])


def _enrich_variable(v: dict, thresholds: dict) -> dict:
    threshold = thresholds.get(v["variable_name"])
    return {
        **v,
        "grade": grade_from_score(v["score"]),
        "direction": direction_of(v["value"], threshold) if threshold else None,
        "golden_value": threshold.golden_value if threshold else None,
        "lower_bound": threshold.lower_bound if threshold else None,
        "upper_bound": threshold.upper_bound if threshold else None,
        "unit": threshold.unit if threshold else None,
    }


@router.get("")
def list_anomalies(db: Session = Depends(get_db)):
    run_detection(db)
    events = db.query(AnomalyEvent).order_by(AnomalyEvent.detected_at.desc()).all()
    thresholds = {t.variable_name: t for t in db.query(VariableThreshold).all()}
    return [
        {
            "id": e.id,
            "process_name": e.process_name,
            "detected_at": e.detected_at.isoformat(),
            "last_updated_at": e.last_updated_at.isoformat(),
            "duration_minutes": e.duration_minutes,
            "severity_grade": e.severity_grade,
            "anomaly_score": e.anomaly_score,
            "status": e.status,
            "variables": [_enrich_variable(v, thresholds) for v in e.variables],
        }
        for e in events
    ]


def _variables_response(all_variables: list[dict]) -> list[dict]:
    return [
        {
            "variable_name": v["variable_name"],
            "contribution_pct": v["contribution_pct"],
            "current_value": v["current_value"],
            "golden_value": v["threshold"].golden_value if v["threshold"] else None,
            "lower_bound": v["threshold"].lower_bound if v["threshold"] else None,
            "upper_bound": v["threshold"].upper_bound if v["threshold"] else None,
            "unit": v["threshold"].unit if v["threshold"] else None,
        }
        for v in all_variables
    ]


@router.get("/{anomaly_event_id}/variables")
def get_variables(anomaly_event_id: str, db: Session = Depends(get_db)):
    event = db.query(AnomalyEvent).filter(AnomalyEvent.id == anomaly_event_id).first()
    if event is None:
        raise HTTPException(status_code=404, detail="해당 이상 건을 찾을 수 없습니다.")

    all_variables = compute_variable_causes(db, event)
    return _variables_response(all_variables)


@router.get("/{anomaly_event_id}/causes")
def get_causes(anomaly_event_id: str, db: Session = Depends(get_db)):
    event = db.query(AnomalyEvent).filter(AnomalyEvent.id == anomaly_event_id).first()
    if event is None:
        raise HTTPException(status_code=404, detail="해당 이상 건을 찾을 수 없습니다.")

    _, causes = analyze_causes(db, anomaly_event_id)
    return {"causes": causes}


@router.get("/{anomaly_event_id}/quality-impact")
def get_quality_impact(anomaly_event_id: str, db: Session = Depends(get_db)):
    event = db.query(AnomalyEvent).filter(AnomalyEvent.id == anomaly_event_id).first()
    if event is None:
        raise HTTPException(status_code=404, detail="해당 이상 건을 찾을 수 없습니다.")
    return predict_quality_impact(db, anomaly_event_id)


@router.post("/{anomaly_event_id}/start-action")
def post_start_action(anomaly_event_id: str, db: Session = Depends(get_db)):
    event = start_action(db, anomaly_event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="해당 이상 건을 찾을 수 없습니다.")
    return {"id": event.id, "status": event.status}


@router.get("/{anomaly_event_id}/quality-prediction")
def get_quality_prediction(anomaly_event_id: str, db: Session = Depends(get_db)):
    prediction = predict_quality(db, anomaly_event_id)
    if prediction is None:
        raise HTTPException(status_code=404, detail="해당 이상 건을 찾을 수 없습니다.")
    return {
        "impact_label": prediction.impact_label,
        "description": prediction.description,
        "confidence_pct": prediction.confidence_pct,
    }


@router.get("/{anomaly_event_id}/recommended-actions")
def get_recommended_actions(anomaly_event_id: str, db: Session = Depends(get_db)):
    results = recommend_actions(db, anomaly_event_id)
    return [
        {
            "rank": r.rank,
            "priority": r.priority,
            "action_name": r.action_name,
            "description": r.description,
            "score": r.score,
            "variable_name": r.variable_name,
            "current_value": r.current_value,
            "target_value": r.target_value,
            "unit": r.unit,
            "expected_effect": r.expected_effect,
        }
        for r in results
    ]


@router.post("/{anomaly_event_id}/action-records")
def post_action_record(anomaly_event_id: str, payload: ActionRecordRequest, db: Session = Depends(get_db)):
    record = submit_action_record(
        db,
        anomaly_event_id,
        worker_id=payload.worker_id,
        selected_action_id=payload.selected_action_id,
        action_content=payload.action_content,
        extra_notes=payload.extra_notes,
    )
    if record is None:
        raise HTTPException(status_code=404, detail="해당 이상 건을 찾을 수 없습니다.")
    return {
        "id": record.id,
        "anomaly_event_id": record.anomaly_event_id,
        "status": "조치완료",
        "notification_sent": record.notification_sent,
        "manager_confirmed": record.manager_confirmed,
        "tentative_result": record.tentative_result,
        "recorded_at": record.recorded_at.isoformat(),
    }
