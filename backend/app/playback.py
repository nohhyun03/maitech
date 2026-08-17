import time
from datetime import timedelta

from sqlalchemy import func

SPEED_MULTIPLIER = 5

_state = {
    "scenario_id": None,
    "base_time": None,
    "end_time": None,
    "accumulated_elapsed": 0.0,
    "running_since": None,
}


def _find_scenario_range(db, scenario_id=None):
    from .models import ProcessData, Scenario

    scenario = (
        db.query(Scenario).filter(Scenario.id == scenario_id).first()
        if scenario_id
        else db.query(Scenario).order_by(Scenario.id).first()
    )
    if scenario is None:
        return None, None, None

    base_time, end_time = (
        db.query(func.min(ProcessData.timestamp), func.max(ProcessData.timestamp))
        .filter(ProcessData.scenario_id == scenario.id)
        .first()
    )
    if base_time is None:
        return None, None, None

    return scenario.id, base_time, end_time


def start(db, scenario_id=None):
    if _state["scenario_id"] is not None:
        return

    scenario_id, base_time, end_time = _find_scenario_range(db, scenario_id)
    if scenario_id is None:
        return

    _state["scenario_id"] = scenario_id
    _state["base_time"] = base_time
    _state["end_time"] = end_time
    _state["accumulated_elapsed"] = 0.0
    _state["running_since"] = time.monotonic()


def restart():
    if _state["scenario_id"] is None:
        return
    _state["accumulated_elapsed"] = 0.0
    _state["running_since"] = time.monotonic()


def pause():
    if _state["scenario_id"] is None or _state["running_since"] is None:
        return
    _state["accumulated_elapsed"] += (time.monotonic() - _state["running_since"]) * SPEED_MULTIPLIER
    _state["running_since"] = None


def resume():
    if _state["scenario_id"] is None or _state["running_since"] is not None:
        return
    _state["running_since"] = time.monotonic()


def current_scenario_time():
    if _state["scenario_id"] is None:
        return None
    elapsed = _state["accumulated_elapsed"]
    if _state["running_since"] is not None:
        elapsed += (time.monotonic() - _state["running_since"]) * SPEED_MULTIPLIER
    current = _state["base_time"] + timedelta(seconds=elapsed)
    end_time = _state["end_time"]
    if end_time is not None and current > end_time:
        return end_time
    return current


def active_scenario_id():
    return _state["scenario_id"]


def is_finished():
    if _state["scenario_id"] is None or _state["end_time"] is None:
        return False
    return current_scenario_time() >= _state["end_time"]


def is_running():
    return _state["scenario_id"] is not None and _state["running_since"] is not None and not is_finished()


def is_started():
    return _state["scenario_id"] is not None
