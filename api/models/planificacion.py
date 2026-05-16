from datetime import datetime, UTC
from sqlalchemy import ForeignKey, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from api.database import Base


class Planificacion(Base):
    __tablename__ = "planificaciones_legacy"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    educational_center_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("educational_centers.id"), nullable=True
    )
    nombre: Mapped[str] = mapped_column(String(200))
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    nivel: Mapped[str | None] = mapped_column(String(100), nullable=True)
    periodo_inicio: Mapped[str | None] = mapped_column(String(20), nullable=True)
    periodo_fin: Mapped[str | None] = mapped_column(String(20), nullable=True)
    espacios_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    chat_exportado: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
