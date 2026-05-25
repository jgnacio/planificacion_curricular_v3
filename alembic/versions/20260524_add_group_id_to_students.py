"""add group_id to students

Revision ID: add_group_id_to_students
Revises: add_chat_sessions
Create Date: 2026-05-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "add_group_id_to_students"
down_revision: Union[str, Sequence[str], None] = "add_chat_sessions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("students") as batch_op:
        batch_op.add_column(sa.Column("group_id", sa.String(36), nullable=True))
        batch_op.create_foreign_key("fk_students_group_id", "groups", ["group_id"], ["id"], ondelete="SET NULL")
        batch_op.create_index("ix_students_group_id", ["group_id"])


def downgrade() -> None:
    with op.batch_alter_table("students") as batch_op:
        batch_op.drop_index("ix_students_group_id")
        batch_op.drop_column("group_id")
