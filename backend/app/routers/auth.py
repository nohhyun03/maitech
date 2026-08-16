from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import playback
from ..database import get_db
from ..models import User
from ..schemas import LoginRequest, LoginResponse
from ..security import verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다.")
    playback.start_if_needed(db)
    return LoginResponse(id=user.id, username=user.username, role=user.role, name=user.name)
