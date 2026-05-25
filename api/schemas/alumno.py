from datetime import datetime
from pydantic import BaseModel


class AlumnoCreate(BaseModel):
    nombre_completo: str
    fecha_nacimiento: str | None = None
    nivel: str | None = None
    grado: str | None = None
    notas: str | None = None
    group_id: str | None = None


class AlumnoUpdate(BaseModel):
    nombre_completo: str | None = None
    fecha_nacimiento: str | None = None
    nivel: str | None = None
    grado: str | None = None
    notas: str | None = None
    group_id: str | None = None


class AlumnoRead(BaseModel):
    id: int
    user_id: str
    nombre_completo: str
    fecha_nacimiento: str | None
    nivel: str | None
    grado: str | None
    notas: str | None
    group_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
