from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import scenario_control
from ..database import get_db

router = APIRouter(prefix="/api/scenario", tags=["scenario"])


@router.get("/status")
def get_status(db: Session = Depends(get_db)):
    return scenario_control.get_status(db)


@router.post("/start")
def post_start(db: Session = Depends(get_db)):
    return scenario_control.start(db)


@router.post("/restart")
def post_restart(db: Session = Depends(get_db)):
    return scenario_control.restart(db)


@router.post("/pause")
def post_pause(db: Session = Depends(get_db)):
    return scenario_control.pause(db)


@router.post("/resume")
def post_resume(db: Session = Depends(get_db)):
    return scenario_control.resume(db)
