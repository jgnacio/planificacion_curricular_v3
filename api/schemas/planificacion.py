from datetime import datetime
from pydantic import BaseModel


class PlanificacionCreate(BaseModel):
    nombre: str
    descripcion: str | None = None
    nivel: str | None = None
    periodo_inicio: str | None = None
    periodo_fin: str | None = None
    espacios_json: str | None = None
    chat_exportado: str | None = None


class PlanificacionUpdate(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None
    nivel: str | None = None
    periodo_inicio: str | None = None
    periodo_fin: str | None = None
    espacios_json: str | None = None
    chat_exportado: str | None = None


class PlanificacionRead(BaseModel):
    id: int
    nombre: str
    descripcion: str | None
    nivel: str | None
    periodo_inicio: str | None
    periodo_fin: str | None
    espacios_json: str | None
    chat_exportado: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
