from datetime import datetime
from pydantic import BaseModel


class StudentReportCreate(BaseModel):
    diagnostico: str
    recomendaciones_especialista: str


class StudentReportUpdate(BaseModel):
    diagnostico: str | None = None
    recomendaciones_especialista: str | None = None
    informe_pdf_url: str | None = None


class StudentReportRead(BaseModel):
    id: int
    alumno_id: int
    user_id: str
    diagnostico: str
    recomendaciones_especialista: str
    informe_pdf_url: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
