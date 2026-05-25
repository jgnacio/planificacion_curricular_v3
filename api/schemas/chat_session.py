from datetime import datetime
from pydantic import BaseModel


class ChatSessionCreate(BaseModel):
    ap_session_id: str
    title: str


class ChatSessionRead(BaseModel):
    id: str
    ap_session_id: str
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionList(BaseModel):
    sessions: list[ChatSessionRead]


class SessionMessage(BaseModel):
    role: str  # "user" | "agent"
    text: str
