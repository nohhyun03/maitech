from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ActionRecord

router = APIRouter(prefix="/api/action-records", tags=["action-records"])


@router.get("")
def list_action_records(db: Session = Depends(get_db)):
    records = (
        db.query(ActionRecord)
        .filter(ActionRecord.manager_confirmed.is_(False))
        .order_by(ActionRecord.recorded_at.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "anomaly_event_id": r.anomaly_event_id,
            "process_name": r.anomaly_event.process_name,
            "issue_type": ", ".join(v["variable_name"] for v in r.anomaly_event.variables) + " 이상",
            "action_content": r.action_content,
            "extra_notes": r.extra_notes,
            "manager_confirmed": r.manager_confirmed,
            "recorded_at": r.recorded_at.isoformat(),
        }
        for r in records
        if r.anomaly_event is not None
    ]


@router.post("/{record_id}/confirm")
def confirm_action_record(record_id: int, db: Session = Depends(get_db)):
    record = db.query(ActionRecord).filter(ActionRecord.id == record_id).first()
    if record is None:
        raise HTTPException(status_code=404, detail="해당 조치 기록을 찾을 수 없습니다.")
    record.manager_confirmed = True
    db.commit()
    return {"id": record.id, "manager_confirmed": record.manager_confirmed}
