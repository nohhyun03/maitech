from sqlalchemy.orm import Session

from .models import ActionRecord, AnomalyEvent, User
from .quality_prediction import predict_quality


def start_action(db: Session, anomaly_event_id: str):
    event = db.query(AnomalyEvent).filter(AnomalyEvent.id == anomaly_event_id).first()
    if event is None:
        return None

    if event.status == "미확인":
        event.status = "조치중"
        db.commit()
        db.refresh(event)

    return event


def submit_action_record(
    db: Session,
    anomaly_event_id: str,
    worker_id: int,
    selected_action_id,
    action_content: str,
    extra_notes,
):
    event = db.query(AnomalyEvent).filter(AnomalyEvent.id == anomaly_event_id).first()
    if event is None:
        return None

    manager = db.query(User).filter(User.role == "manager").first()
    prediction = predict_quality(db, anomaly_event_id)
    tentative_result = (
        {
            "impact_label": prediction.impact_label,
            "confidence_pct": prediction.confidence_pct,
            "description": prediction.description,
        }
        if prediction is not None
        else None
    )

    record = ActionRecord(
        anomaly_event_id=anomaly_event_id,
        worker_id=worker_id,
        selected_action_id=selected_action_id,
        action_content=action_content,
        extra_notes=extra_notes,
        sender_id=manager.id if manager else worker_id,
        receiver_id=worker_id,
        notification_sent=True,
        manager_confirmed=False,
        tentative_result=tentative_result,
    )
    db.add(record)

    event.status = "조치완료"

    db.commit()
    db.refresh(record)
    return record
