from datetime import datetime, UTC
from sqlalchemy import ForeignKey, String, Text, DateTime, Integer, UniqueConstraint, JSON
from sqlalchemy.orm import Mapped, mapped_column
from api.database import Base


class DescripcionFundada(Base):
    __tablename__ = "descripciones_fundadas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    alumno_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    bimestre: Mapped[int] = mapped_column(Integer, nullable=False)
    anio: Mapped[int] = mapped_column(Integer, nullable=False)
    espacios_desempeno: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    desempeno_relacional: Mapped[str] = mapped_column(Text, nullable=False)
    sugerencias: Mapped[str] = mapped_column(Text, nullable=False)
    descripcion_generada: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        UniqueConstraint("alumno_id", "bimestre", "anio", name="uq_descripcion_alumno_bimestre_anio"),
    )
