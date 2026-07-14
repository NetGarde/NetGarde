"""rename twin_alerts.trusttwin_device_id to device_id

Revision ID: u6v7w8x9y0z1
Revises: t5u6v7w8x9y0
Create Date: 2026-07-14 21:10:00.000000
"""

from typing import Sequence, Union

from alembic import op

revision: str = "u6v7w8x9y0z1"
down_revision: Union[str, Sequence[str], None] = "t5u6v7w8x9y0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_twin_alerts_device_ts", table_name="twin_alerts")
    op.drop_index(op.f("ix_twin_alerts_trusttwin_device_id"), table_name="twin_alerts")
    op.alter_column("twin_alerts", "trusttwin_device_id", new_column_name="device_id")
    op.create_index(op.f("ix_twin_alerts_device_id"), "twin_alerts", ["device_id"], unique=False)
    op.create_index("ix_twin_alerts_device_ts", "twin_alerts", ["device_id", "timestamp"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_twin_alerts_device_ts", table_name="twin_alerts")
    op.drop_index(op.f("ix_twin_alerts_device_id"), table_name="twin_alerts")
    op.alter_column("twin_alerts", "device_id", new_column_name="trusttwin_device_id")
    op.create_index(
        op.f("ix_twin_alerts_trusttwin_device_id"),
        "twin_alerts",
        ["trusttwin_device_id"],
        unique=False,
    )
    op.create_index(
        "ix_twin_alerts_device_ts",
        "twin_alerts",
        ["trusttwin_device_id", "timestamp"],
        unique=False,
    )
