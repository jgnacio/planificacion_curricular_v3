"""jerarquia_ebi

Revision ID: a3f8c1d92b74
Revises: 14a29ce47c25
Create Date: 2026-05-15 00:00:00.000000

"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3f8c1d92b74'
down_revision: Union[str, Sequence[str], None] = '14a29ce47c25'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Paso 1: renombrar tabla legada
    op.rename_table('planificaciones', 'planificaciones_legacy')

    # Paso 2: crear tabla groups
    op.create_table(
        'groups',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(200), nullable=False),
        sa.Column('educational_center_id', sa.String(36), nullable=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('stage', sa.String(50), nullable=True),
        sa.Column('level', sa.String(100), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ['educational_center_id'], ['educational_centers.id'],
            name='fk_groups_educational_center',
            ondelete='SET NULL',
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_groups_user_id'), 'groups', ['user_id'], unique=False)

    # Paso 3: crear tabla integrative_projects
    op.create_table(
        'integrative_projects',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('group_id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(200), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('purpose', sa.Text(), nullable=True),
        sa.Column('duration_weeks', sa.Integer(), nullable=True),
        sa.Column('final_product', sa.Text(), nullable=True),
        sa.Column('curriculum_space_ids', sa.Text(), nullable=True),
        sa.Column('competency_ids', sa.Text(), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ['group_id'], ['groups.id'],
            name='fk_integrative_projects_group',
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_integrative_projects_group_id'), 'integrative_projects', ['group_id'], unique=False)
    op.create_index(op.f('ix_integrative_projects_user_id'), 'integrative_projects', ['user_id'], unique=False)

    # Paso 4: crear tabla activity_sequences
    op.create_table(
        'activity_sequences',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('learning_goal', sa.Text(), nullable=True),
        sa.Column('order', sa.Integer(), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ['project_id'], ['integrative_projects.id'],
            name='fk_activity_sequences_project',
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_activity_sequences_project_id'), 'activity_sequences', ['project_id'], unique=False)

    # Paso 5: crear tabla activities
    op.create_table(
        'activities',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(200), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=True),
        sa.Column('sequence_id', sa.String(36), nullable=True),
        sa.Column('group_id', sa.String(36), nullable=True),
        sa.Column('order', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ['project_id'], ['integrative_projects.id'],
            name='fk_activities_project',
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['sequence_id'], ['activity_sequences.id'],
            name='fk_activities_sequence',
            ondelete='SET NULL',
        ),
        sa.ForeignKeyConstraint(
            ['group_id'], ['groups.id'],
            name='fk_activities_group',
            ondelete='SET NULL',
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_activities_user_id'), 'activities', ['user_id'], unique=False)
    op.create_index(op.f('ix_activities_project_id'), 'activities', ['project_id'], unique=False)
    op.create_index(op.f('ix_activities_group_id'), 'activities', ['group_id'], unique=False)

    # Paso 6: migrar datos de planificaciones_legacy → activities
    bind = op.get_bind()
    is_pg = bind.dialect.name == 'postgresql'

    if is_pg:
        op.execute("""
            INSERT INTO activities (id, user_id, project_id, sequence_id, group_id, "order", title, content, created_at, updated_at)
            SELECT gen_random_uuid()::text, user_id, NULL, NULL, NULL, 0, nombre, chat_exportado, created_at, updated_at
            FROM planificaciones_legacy
        """)
    else:
        # SQLite: insertar fila a fila con uuid de Python
        legacy = bind.execute(sa.text(
            "SELECT user_id, nombre, chat_exportado, created_at, updated_at FROM planificaciones_legacy"
        )).fetchall()
        for row in legacy:
            bind.execute(sa.text(
                'INSERT INTO activities (id, user_id, project_id, sequence_id, group_id, "order", title, content, created_at, updated_at) '
                'VALUES (:id, :user_id, NULL, NULL, NULL, 0, :title, :content, :created_at, :updated_at)'
            ), {
                'id': str(uuid.uuid4()),
                'user_id': row[0],
                'title': row[1],
                'content': row[2],
                'created_at': row[3],
                'updated_at': row[4],
            })


def downgrade() -> None:
    # Invertir en orden correcto (FK deps)
    op.drop_index(op.f('ix_activities_group_id'), table_name='activities')
    op.drop_index(op.f('ix_activities_project_id'), table_name='activities')
    op.drop_index(op.f('ix_activities_user_id'), table_name='activities')
    op.drop_table('activities')

    op.drop_index(op.f('ix_activity_sequences_project_id'), table_name='activity_sequences')
    op.drop_table('activity_sequences')

    op.drop_index(op.f('ix_integrative_projects_user_id'), table_name='integrative_projects')
    op.drop_index(op.f('ix_integrative_projects_group_id'), table_name='integrative_projects')
    op.drop_table('integrative_projects')

    op.drop_index(op.f('ix_groups_user_id'), table_name='groups')
    op.drop_table('groups')

    op.rename_table('planificaciones_legacy', 'planificaciones')
