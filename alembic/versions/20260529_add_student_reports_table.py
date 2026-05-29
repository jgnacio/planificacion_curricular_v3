"""add student_reports table

Revision ID: add_student_reports_table
Revises: add_group_id_to_students
Create Date: 2026-05-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "add_student_reports_table"
down_revision: Union[str, Sequence[str], None] = "add_group_id_to_students"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "student_reports",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("alumno_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("user_id", sa.String(200), nullable=False, index=True),
        sa.Column("diagnostico", sa.Text(), nullable=False),
        sa.Column("recomendaciones_especialista", sa.Text(), nullable=False),
        sa.Column("informe_pdf_url", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("student_reports")
