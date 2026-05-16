import uuid
from datetime import datetime, date, UTC
from sqlalchemy import ForeignKey, String, DateTime, Text, Integer, Date
from sqlalchemy.orm import Mapped, mapped_column
from api.database import Base


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(200), ForeignKey("users_profile.clerk_user_id"), nullable=False, index=True
    )
    project_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("integrative_projects.id", ondelete="CASCADE"), nullable=True, index=True
    )
    sequence_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("activity_sequences.id", ondelete="SET NULL"), nullable=True
    )
    group_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("groups.id", ondelete="SET NULL"), nullable=True, index=True
    )
    order: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)           # columna legada — no dropear
    raw_content: Mapped[str | None] = mapped_column(Text, nullable=True)       # blob JSON del agente IA
    activity_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    curriculum_space: Mapped[str | None] = mapped_column(String(200), nullable=True)
    curriculum_unit: Mapped[str | None] = mapped_column(String(200), nullable=True)
    stage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    specific_competency_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    specific_competency: Mapped[str | None] = mapped_column(Text, nullable=True)
    curriculum_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    achievement_criterion: Mapped[str | None] = mapped_column(Text, nullable=True)
    learning_goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    methodology: Mapped[str | None] = mapped_column(String(200), nullable=True)
    general_competencies: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array string
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default='draft')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )
