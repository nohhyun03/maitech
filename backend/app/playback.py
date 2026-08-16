import time
from datetime import timedelta

from sqlalchemy import func

SPEED_MULTIPLIER = 10

_state = {"scenario_id": None, "started_real": None, "base_time": None}


def start_if_needed(db, scenario_id=None):
    if _state["started_real"] is not None:
        return

    from .models import ProcessData, Scenario

    scenario = (
        db.query(Scenario).filter(Scenario.id == scenario_id).first()
        if scenario_id
        else db.query(Scenario).order_by(Scenario.id).first()
    )
    if scenario is None:
        return

    base_time = (
        db.query(func.min(ProcessData.timestamp))
        .filter(ProcessData.scenario_id == scenario.id)
        .scalar()
    )
    if base_time is None:
        return

    _state["scenario_id"] = scenario.id
    _state["started_real"] = time.monotonic()
    _state["base_time"] = base_time


def current_scenario_time():
    if _state["started_real"] is None:
        return None
    elapsed = time.monotonic() - _state["started_real"]
    return _state["base_time"] + timedelta(seconds=elapsed * SPEED_MULTIPLIER)


def active_scenario_id():
    return _state["scenario_id"]
