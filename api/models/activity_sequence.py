import uuid
from datetime import datetime, date, UTC
from sqlalchemy import ForeignKey, String, DateTime, Text, Date, Integer
from sqlalchemy.orm import Mapped, mapped_column
from api.database import Base


class ActivitySequence(Base):
    __tablename__ = "activity_sequences"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("integrative_projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(200), ForeignKey("users_profile.clerk_user_id"), nullable=False, server_default="", index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    learning_goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    order: Mapped[int] = mapped_column(Integer, default=0)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )
