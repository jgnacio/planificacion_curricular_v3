from datetime import datetime, date
from pydantic import BaseModel


class ActivitySequenceCreate(BaseModel):
    name: str
    project_id: str
    learning_goal: str | None = None
    order: int = 0
    start_date: date | None = None
    end_date: date | None = None


class ActivitySequenceUpdate(BaseModel):
    name: str | None = None
    learning_goal: str | None = None
    order: int | None = None
    start_date: date | None = None
    end_date: date | None = None


class ActivitySequenceRead(BaseModel):
    id: str
    project_id: str
    user_id: str
    name: str
    learning_goal: str | None
    order: int
    start_date: date | None
    end_date: date | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
