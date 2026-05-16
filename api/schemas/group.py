from datetime import datetime, date
from pydantic import BaseModel


class GroupCreate(BaseModel):
    name: str
    stage: str | None = None
    level: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    description: str | None = None
    educational_center_id: str | None = None


class GroupUpdate(BaseModel):
    name: str | None = None
    stage: str | None = None
    level: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    description: str | None = None
    educational_center_id: str | None = None


class GroupRead(BaseModel):
    id: str
    user_id: str
    name: str
    stage: str | None
    level: str | None
    start_date: date | None
    end_date: date | None
    description: str | None
    educational_center_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
