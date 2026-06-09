"""add descripciones_fundadas table

Revision ID: add_descripciones_fundadas
Revises: add_student_reports_table
Create Date: 2026-06-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "add_descripciones_fundadas"
down_revision: Union[str, Sequence[str], None] = "add_student_reports_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "descripciones_fundadas",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("alumno_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("user_id", sa.String(200), nullable=False, index=True),
        sa.Column("bimestre", sa.Integer(), nullable=False),
        sa.Column("anio", sa.Integer(), nullable=False),
        sa.Column("espacios_desempeno", sa.JSON(), nullable=False),
        sa.Column("desempeno_relacional", sa.Text(), nullable=False),
        sa.Column("sugerencias", sa.Text(), nullable=False),
        sa.Column("descripcion_generada", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("alumno_id", "bimestre", "anio", name="uq_descripcion_alumno_bimestre_anio"),
    )


def downgrade() -> None:
    op.drop_table("descripciones_fundadas")
