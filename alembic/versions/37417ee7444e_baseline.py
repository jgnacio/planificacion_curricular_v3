"""baseline

Revision ID: 37417ee7444e
Revises:
Create Date: 2026-05-01 15:31:01.570461

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '37417ee7444e'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = inspector.get_table_names()

    if 'alumnos' not in existing:
        op.create_table(
            'alumnos',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.String(length=200), nullable=False),
            sa.Column('nombre_completo', sa.String(length=200), nullable=False),
            sa.Column('fecha_nacimiento', sa.String(length=20), nullable=True),
            sa.Column('nivel', sa.String(length=50), nullable=True),
            sa.Column('grado', sa.String(length=50), nullable=True),
            sa.Column('notas', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_alumnos_id', 'alumnos', ['id'], unique=False)
        op.create_index('ix_alumnos_user_id', 'alumnos', ['user_id'], unique=False)

    if 'planificaciones' not in existing:
        op.create_table(
            'planificaciones',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.String(length=200), nullable=False),
            sa.Column('nombre', sa.String(length=200), nullable=False),
            sa.Column('descripcion', sa.Text(), nullable=True),
            sa.Column('nivel', sa.String(length=100), nullable=True),
            sa.Column('periodo_inicio', sa.String(length=20), nullable=True),
            sa.Column('periodo_fin', sa.String(length=20), nullable=True),
            sa.Column('espacios_json', sa.Text(), nullable=True),
            sa.Column('chat_exportado', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_planificaciones_id', 'planificaciones', ['id'], unique=False)
        op.create_index('ix_planificaciones_user_id', 'planificaciones', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_planificaciones_user_id', table_name='planificaciones')
    op.drop_index('ix_planificaciones_id', table_name='planificaciones')
    op.drop_table('planificaciones')
    op.drop_index('ix_alumnos_user_id', table_name='alumnos')
    op.drop_index('ix_alumnos_id', table_name='alumnos')
    op.drop_table('alumnos')
