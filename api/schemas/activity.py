from datetime import datetime, date
from pydantic import BaseModel


class ActivityCreate(BaseModel):
    title: str
    raw_content: str | None = None
    project_id: str | None = None
    sequence_id: str | None = None
    group_id: str | None = None
    order: int = 0
    activity_type: str | None = None
    curriculum_space: str | None = None
    curriculum_unit: str | None = None
    stage: int | None = None
    specific_competency_code: str | None = None
    specific_competency: str | None = None
    curriculum_content: str | None = None
    achievement_criterion: str | None = None
    learning_goal: str | None = None
    methodology: str | None = None
    general_competencies: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    status: str = 'draft'


class ActivityUpdate(BaseModel):
    title: str | None = None
    raw_content: str | None = None
    project_id: str | None = None
    sequence_id: str | None = None
    group_id: str | None = None
    order: int | None = None
    activity_type: str | None = None
    curriculum_space: str | None = None
    curriculum_unit: str | None = None
    stage: int | None = None
    specific_competency_code: str | None = None
    specific_competency: str | None = None
    curriculum_content: str | None = None
    achievement_criterion: str | None = None
    learning_goal: str | None = None
    methodology: str | None = None
    general_competencies: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    status: str | None = None


class ActivityRead(BaseModel):
    id: str
    user_id: str
    project_id: str | None
    sequence_id: str | None
    group_id: str | None
    order: int
    title: str
    raw_content: str | None
    activity_type: str | None
    curriculum_space: str | None
    curriculum_unit: str | None
    stage: int | None
    specific_competency_code: str | None
    specific_competency: str | None
    curriculum_content: str | None
    achievement_criterion: str | None
    learning_goal: str | None
    methodology: str | None
    general_competencies: str | None
    period_start: date | None
    period_end: date | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
