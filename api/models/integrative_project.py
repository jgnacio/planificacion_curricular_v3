import uuid
from datetime import datetime, date, UTC
from sqlalchemy import ForeignKey, String, DateTime, Text, Date, Integer
from sqlalchemy.orm import Mapped, mapped_column
from api.database import Base


class IntegrativeProject(Base):
    __tablename__ = "integrative_projects"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    group_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(200), ForeignKey("users_profile.clerk_user_id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    purpose: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_weeks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    final_product: Mapped[str | None] = mapped_column(Text, nullable=True)
    curriculum_space_ids: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array of IDs
    competency_ids: Mapped[str | None] = mapped_column(Text, nullable=True)        # JSON array of IDs
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )
