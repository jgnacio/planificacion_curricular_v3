import uuid
from datetime import datetime, date, UTC
from sqlalchemy import ForeignKey, String, DateTime, Text, Date
from sqlalchemy.orm import Mapped, mapped_column
from api.database import Base


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(200), ForeignKey("users_profile.clerk_user_id"), nullable=False, index=True
    )
    educational_center_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("educational_centers.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    stage: Mapped[str | None] = mapped_column(String(50), nullable=True)
    level: Mapped[str | None] = mapped_column(String(100), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )
