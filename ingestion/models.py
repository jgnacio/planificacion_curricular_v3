from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class CompetenciaEspecifica:
    id: str
    enunciado: str = ""
    desarrollo: str = ""
    ejes: str = ""
    mcn: str = ""
    padre: Optional[str] = None
    nivel_pertenencia: str = "" # ESPACIO, UNIDAD, TRAMO

    def __repr__(self):
        return f"CE({self.id})"
