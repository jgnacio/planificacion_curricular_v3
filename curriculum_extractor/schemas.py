"""Pydantic schemas for the curriculum extractor output."""

from pydantic import BaseModel


class CompetenciaMCN(BaseModel):
    codigo: str   # "MCN1" .. "MCN10"
    nombre: str
    descripcion: str


class CEOutput(BaseModel):
    codigo: str         # "CE1", "CE2", etc.
    texto: str          # Full CE description text
    mcn: list[str] = [] # MCN references (empty by default)


class MateriaOutput(BaseModel):
    nombre: str
    competencias_especificas: list[CEOutput]
    contenidos: list[str]   # flat list — merger distributes to grade keys
    criterios: list[str]    # flat list — merger distributes to grade keys
    patron_detectado: str   # "P1", "C2-P6", etc.


# --- Output schema (matches teacher_agent/agent.py expectations) ---

class MateriaJSON(BaseModel):
    nombre: str
    competencias_especificas: list[dict]        # [{"codigo": ..., "texto": ..., "mcn": [...]}]
    contenidos: dict[str, list[str]]            # {"3er_grado": [...], "4to_grado": [...]}
    criterios: dict[str, list[str]]             # {"3er_grado": [...], "4to_grado": [...]}


class EspacioJSON(BaseModel):
    nombre: str
    materias: dict[str, MateriaJSON]            # {materia_key: MateriaJSON}


class TramoJSON(BaseModel):
    label: str
    espacios: dict[str, EspacioJSON]            # {espacio_key: EspacioJSON}


class CurriculumOutput(BaseModel):
    metadata: dict                              # includes competencias_mcn
    tramos: dict[str, TramoJSON]               # tramo_1..tramo_4
