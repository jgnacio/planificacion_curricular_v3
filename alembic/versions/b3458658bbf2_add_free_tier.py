"""add_free_tier

Revision ID: b3458658bbf2
Revises: add_descripciones_fundadas
Create Date: 2026-06-16 23:07:50.098517

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3458658bbf2'
down_revision: Union[str, Sequence[str], None] = 'add_descripciones_fundadas'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('user_free_state',
    sa.Column('user_id', sa.String(length=200), nullable=False),
    sa.Column('trial_starts_at', sa.DateTime(), nullable=True),
    sa.Column('trial_ends_at', sa.DateTime(), nullable=True),
    sa.Column('monthly_plan_count', sa.Integer(), nullable=False),
    sa.Column('ebi_query_count', sa.Integer(), nullable=False),
    sa.Column('monthly_reset_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users_profile.clerk_user_id'], ),
    sa.PrimaryKeyConstraint('user_id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('user_free_state')
