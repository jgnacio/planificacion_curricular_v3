"""add_used_licenses_trigger

Revision ID: 14a29ce47c25
Revises: 52e29e4dd2a9
Create Date: 2026-05-01 15:39:38.549502

"""
from typing import Sequence, Union

from alembic import op


revision: str = '14a29ce47c25'
down_revision: Union[str, Sequence[str], None] = '52e29e4dd2a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_FUNCTION = """
CREATE OR REPLACE FUNCTION fn_sync_used_licenses()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE institution_tenants
    SET used_licenses = (
        SELECT COUNT(*) FROM licenses
        WHERE institution_tenant_id = COALESCE(NEW.institution_tenant_id, OLD.institution_tenant_id)
        AND status = 'assigned'
    )
    WHERE id = COALESCE(NEW.institution_tenant_id, OLD.institution_tenant_id);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

_TRIGGER = """
DROP TRIGGER IF EXISTS trg_sync_used_licenses ON licenses;
CREATE TRIGGER trg_sync_used_licenses
AFTER INSERT OR UPDATE OR DELETE ON licenses
FOR EACH ROW EXECUTE FUNCTION fn_sync_used_licenses();
"""


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(_FUNCTION)
        op.execute(_TRIGGER)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_sync_used_licenses ON licenses;")
        op.execute("DROP FUNCTION IF EXISTS fn_sync_used_licenses();")
