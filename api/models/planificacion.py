from datetime import datetime
from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from api.database import Base


class Planificacion(Base):
    __tablename__ = "planificaciones"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(200))
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    nivel: Mapped[str | None] = mapped_column(String(100), nullable=True)
    periodo_inicio: Mapped[str | None] = mapped_column(String(20), nullable=True)
    periodo_fin: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # JSON array de espacios seleccionados almacenado como texto
    espacios_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Contenido del chat del agente asociado a esta planificación
    chat_exportado: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
