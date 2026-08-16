from typing import Optional

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    id: int
    username: str
    role: str
    name: str


class ActionRecordRequest(BaseModel):
    worker_id: int
    selected_action_id: Optional[int] = None
    action_content: str
    extra_notes: Optional[str] = None
