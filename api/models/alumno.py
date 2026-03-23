from datetime import datetime
from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from api.database import Base


class Alumno(Base):
    __tablename__ = "alumnos"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    nombre_completo: Mapped[str] = mapped_column(String(200))
    fecha_nacimiento: Mapped[str | None] = mapped_column(String(20), nullable=True)
    nivel: Mapped[str | None] = mapped_column(String(50), nullable=True)
    grado: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Singularidades como texto libre (JSON opcional)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
