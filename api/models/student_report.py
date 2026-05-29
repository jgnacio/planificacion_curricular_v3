from datetime import datetime, UTC
from sqlalchemy import ForeignKey, String, Text, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column
from api.database import Base


class StudentReport(Base):
    __tablename__ = "student_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    alumno_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    diagnostico: Mapped[str] = mapped_column(Text, nullable=False)
    recomendaciones_especialista: Mapped[str] = mapped_column(Text, nullable=False)
    informe_pdf_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
