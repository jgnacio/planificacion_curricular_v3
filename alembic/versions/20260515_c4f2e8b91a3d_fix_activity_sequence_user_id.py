"""fix_activity_sequence_user_id

Patch: popula user_id desde integrative_projects y agrega índice.
Las filas creadas por la migración anterior quedaron con user_id=''.

Revision ID: c4f2e8b91a3d
Revises: b1e9f2a03c85
Create Date: 2026-05-15 00:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c4f2e8b91a3d'
down_revision: Union[str, Sequence[str], None] = 'b1e9f2a03c85'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Poblar user_id vacío desde el proyecto padre
    op.execute(
        """
        UPDATE activity_sequences
        SET user_id = (
            SELECT user_id FROM integrative_projects
            WHERE integrative_projects.id = activity_sequences.project_id
        )
        WHERE user_id = '' OR user_id IS NULL
        """
    )

    # Agregar índice en user_id para consultas scoped-by-user
    with op.batch_alter_table('activity_sequences') as batch_op:
        batch_op.create_index('ix_activity_sequences_user_id', ['user_id'])


def downgrade() -> None:
    with op.batch_alter_table('activity_sequences') as batch_op:
        batch_op.drop_index('ix_activity_sequences_user_id')
