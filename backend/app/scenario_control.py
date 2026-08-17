from sqlalchemy.orm import Session

from . import detection, playback
from .models import (
    ActionRecord,
    AnomalyEvent,
    CauseSummary,
    QualityImpactSummary,
    QualityPrediction,
    RecommendedAction,
    RecommendedActionSummary,
)


def _clear_scenario_data(db: Session, scenario_id: int):
    event_ids = [e.id for e in db.query(AnomalyEvent).filter(AnomalyEvent.scenario_id == scenario_id).all()]
    if event_ids:
        db.query(ActionRecord).filter(ActionRecord.anomaly_event_id.in_(event_ids)).delete(synchronize_session=False)
        db.query(RecommendedAction).filter(RecommendedAction.anomaly_event_id.in_(event_ids)).delete(synchronize_session=False)
        db.query(RecommendedActionSummary).filter(RecommendedActionSummary.anomaly_event_id.in_(event_ids)).delete(synchronize_session=False)
        db.query(QualityPrediction).filter(QualityPrediction.anomaly_event_id.in_(event_ids)).delete(synchronize_session=False)
        db.query(QualityImpactSummary).filter(QualityImpactSummary.anomaly_event_id.in_(event_ids)).delete(synchronize_session=False)
        db.query(CauseSummary).filter(CauseSummary.anomaly_event_id.in_(event_ids)).delete(synchronize_session=False)
    db.query(AnomalyEvent).filter(AnomalyEvent.scenario_id == scenario_id).delete()
    db.commit()


def get_status(db: Session):
    current_time = playback.current_scenario_time()
    return {
        "started": playback.is_started(),
        "running": playback.is_running(),
        "finished": playback.is_finished(),
        "current_time": current_time.isoformat() if current_time else None,
    }


def start(db: Session):
    playback.start(db)
    return get_status(db)


def restart(db: Session):
    scenario_id = playback.active_scenario_id()
    if scenario_id is None:
        return start(db)

    _clear_scenario_data(db, scenario_id)
    detection.reset_watermark(scenario_id)
    playback.restart()
    return get_status(db)


def pause(db: Session):
    playback.pause()
    return get_status(db)


def resume(db: Session):
    playback.resume()
    return get_status(db)
