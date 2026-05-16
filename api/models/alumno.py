from datetime import datetime, UTC
from sqlalchemy import ForeignKey, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from api.database import Base


class Alumno(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    educational_center_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("educational_centers.id"), nullable=True
    )
    nombre_completo: Mapped[str] = mapped_column(String(200))
    fecha_nacimiento: Mapped[str | None] = mapped_column(String(20), nullable=True)
    nivel: Mapped[str | None] = mapped_column(String(50), nullable=True)
    grado: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
