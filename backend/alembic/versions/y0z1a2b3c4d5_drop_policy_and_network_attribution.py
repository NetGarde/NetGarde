"""drop_policy_and_network_attribution

Revision ID: y0z1a2b3c4d5
Revises: x9y0z1a2b3c4
Create Date: 2026-07-16 14:10:00.000000

Drop soft-policy / quarantine and network-attribution tables that are no
longer fed by the agent stack. Devices and twin_alerts remain.
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "y0z1a2b3c4d5"
down_revision: Union[str, Sequence[str], None] = "x9y0z1a2b3c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        text("ALTER TABLE devices DROP CONSTRAINT IF EXISTS fk_devices_policy_profile_id")
    )
    connection.execute(text("DROP INDEX IF EXISTS ix_devices_policy_profile_id"))
    connection.execute(
        text("ALTER TABLE devices DROP COLUMN IF EXISTS policy_profile_id")
    )
    for table in (
        "device_quarantines",
        "device_app_usage_rollups",
        "device_network_context",
        "policy_profiles",
    ):
        connection.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))


def downgrade() -> None:
    raise NotImplementedError("Downgrade is intentionally unsupported for this cleanup migration.")
