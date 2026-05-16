"""enrich_activity_fields

Revision ID: b1e9f2a03c85
Revises: a3f8c1d92b74
Create Date: 2026-05-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1e9f2a03c85'
down_revision: Union[str, Sequence[str], None] = 'a3f8c1d92b74'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Tabla activities — agregar raw_content y campos estructurados
    #    No se usa rename de columna: se agrega raw_content y se copia
    #    desde content para mantener backward compat (SQLite safe).
    # ------------------------------------------------------------------
    with op.batch_alter_table('activities') as batch_op:
        batch_op.add_column(sa.Column('raw_content', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('activity_type', sa.String(20), nullable=True))
        batch_op.add_column(sa.Column('curriculum_space', sa.String(200), nullable=True))
        batch_op.add_column(sa.Column('curriculum_unit', sa.String(200), nullable=True))
        batch_op.add_column(sa.Column('stage', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('specific_competency_code', sa.String(20), nullable=True))
        batch_op.add_column(sa.Column('specific_competency', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('curriculum_content', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('achievement_criterion', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('learning_goal', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('methodology', sa.String(200), nullable=True))
        batch_op.add_column(sa.Column('general_competencies', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('period_start', sa.Date(), nullable=True))
        batch_op.add_column(sa.Column('period_end', sa.Date(), nullable=True))
        batch_op.add_column(sa.Column('status', sa.String(20), nullable=False, server_default='draft'))

    # Copiar contenido legado a raw_content para no perder datos
    op.execute("UPDATE activities SET raw_content = content WHERE raw_content IS NULL AND content IS NOT NULL")

    # ------------------------------------------------------------------
    # 2. Tabla activity_sequences — agregar user_id para trazabilidad
    # ------------------------------------------------------------------
    with op.batch_alter_table('activity_sequences') as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.String(200), nullable=False, server_default=''))


def downgrade() -> None:
    # ------------------------------------------------------------------
    # 2. Revertir activity_sequences
    # ------------------------------------------------------------------
    with op.batch_alter_table('activity_sequences') as batch_op:
        batch_op.drop_column('user_id')

    # ------------------------------------------------------------------
    # 1. Revertir activities — drop columnas nuevas
    # ------------------------------------------------------------------
    with op.batch_alter_table('activities') as batch_op:
        batch_op.drop_column('status')
        batch_op.drop_column('period_end')
        batch_op.drop_column('period_start')
        batch_op.drop_column('general_competencies')
        batch_op.drop_column('methodology')
        batch_op.drop_column('learning_goal')
        batch_op.drop_column('achievement_criterion')
        batch_op.drop_column('curriculum_content')
        batch_op.drop_column('specific_competency')
        batch_op.drop_column('specific_competency_code')
        batch_op.drop_column('stage')
        batch_op.drop_column('curriculum_unit')
        batch_op.drop_column('curriculum_space')
        batch_op.drop_column('activity_type')
        batch_op.drop_column('raw_content')
