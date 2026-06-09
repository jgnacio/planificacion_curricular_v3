from datetime import datetime
from pydantic import BaseModel, field_validator


ESPACIOS_VALIDOS = {
    "espacio_cientifico_matematico",
    "espacio_comunicacion",
    "espacio_ciencias_sociales",
    "espacio_creativo_artistico",
    "espacio_desarrollo_personal",
    "espacio_tecnico_tecnologico",
}


class EspacioDesempeno(BaseModel):
    nivel_avance: int
    observacion: str

    @field_validator("nivel_avance")
    @classmethod
    def validar_nivel(cls, v: int) -> int:
        if v not in range(1, 6):
            raise ValueError("nivel_avance debe ser entre 1 y 5")
        return v


class DescripcionFundadaCreate(BaseModel):
    bimestre: int
    anio: int
    espacios_desempeno: dict[str, EspacioDesempeno]
    desempeno_relacional: str
    sugerencias: str

    @field_validator("bimestre")
    @classmethod
    def validar_bimestre(cls, v: int) -> int:
        if v not in range(1, 5):
            raise ValueError("bimestre debe ser 1, 2, 3 o 4")
        return v

    @field_validator("espacios_desempeno")
    @classmethod
    def validar_espacios(cls, v: dict) -> dict:
        claves_invalidas = set(v.keys()) - ESPACIOS_VALIDOS
        if claves_invalidas:
            raise ValueError(f"Espacios inválidos: {claves_invalidas}")
        return v


class DescripcionFundadaUpdate(BaseModel):
    bimestre: int | None = None
    anio: int | None = None
    espacios_desempeno: dict[str, EspacioDesempeno] | None = None
    desempeno_relacional: str | None = None
    sugerencias: str | None = None
    descripcion_generada: str | None = None


class DescripcionFundadaGenerarPreview(BaseModel):
    alumno_nombre: str
    alumno_nivel: str = ""
    alumno_grado: str = ""
    bimestre: int
    anio: int
    espacios_desempeno: dict[str, EspacioDesempeno]
    desempeno_relacional: str
    sugerencias: str

    @field_validator("espacios_desempeno")
    @classmethod
    def validar_observaciones(cls, v: dict) -> dict:
        claves_invalidas = set(v.keys()) - ESPACIOS_VALIDOS
        if claves_invalidas:
            raise ValueError(f"Espacios inválidos: {claves_invalidas}")
        con_observacion = sum(1 for e in v.values() if e.observacion.strip())
        if con_observacion < 2:
            raise ValueError("Debe completar la observación de al menos 2 espacios para generar la descripción")
        return v


class DescripcionFundadaRead(BaseModel):
    id: int
    alumno_id: int
    user_id: str
    bimestre: int
    anio: int
    espacios_desempeno: dict
    desempeno_relacional: str
    sugerencias: str
    descripcion_generada: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
