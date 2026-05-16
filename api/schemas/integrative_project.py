import json
from datetime import datetime, date
from pydantic import BaseModel, field_validator


class IntegrativeProjectCreate(BaseModel):
    name: str
    group_id: str
    purpose: str | None = None
    duration_weeks: int | None = None
    final_product: str | None = None
    curriculum_space_ids: list[str] = []
    competency_ids: list[str] = []
    start_date: date | None = None
    end_date: date | None = None

    @field_validator("curriculum_space_ids", "competency_ids", mode="before")
    @classmethod
    def parse_json_list(cls, v: object) -> list[str]:
        """Acepta tanto lista como JSON string al recibir desde el cliente."""
        if isinstance(v, str):
            return json.loads(v)
        return v if v is not None else []


class IntegrativeProjectUpdate(BaseModel):
    name: str | None = None
    purpose: str | None = None
    duration_weeks: int | None = None
    final_product: str | None = None
    curriculum_space_ids: list[str] | None = None
    competency_ids: list[str] | None = None
    start_date: date | None = None
    end_date: date | None = None

    @field_validator("curriculum_space_ids", "competency_ids", mode="before")
    @classmethod
    def parse_json_list(cls, v: object) -> list[str] | None:
        """Acepta tanto lista como JSON string al recibir desde el cliente."""
        if isinstance(v, str):
            return json.loads(v)
        return v


class IntegrativeProjectRead(BaseModel):
    id: str
    group_id: str
    user_id: str
    name: str
    purpose: str | None
    duration_weeks: int | None
    final_product: str | None
    curriculum_space_ids: list[str]
    competency_ids: list[str]
    start_date: date | None
    end_date: date | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("curriculum_space_ids", "competency_ids", mode="before")
    @classmethod
    def parse_json_list(cls, v: object) -> list[str]:
        """Parsea el JSON string almacenado en DB a lista de strings."""
        if isinstance(v, str):
            return json.loads(v)
        return v if v is not None else []
