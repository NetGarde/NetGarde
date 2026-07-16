"""recreate twin_alerts table

Revision ID: a2b3c4d5e6f7
Revises: z1a2b3c4d5e6
Create Date: 2026-07-16 18:15:00.000000

Restore durable detection alerts for detection-engine ingest and Alerts UI.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, Sequence[str], None] = "z1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "twin_alerts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("device_id", sa.String(length=64), nullable=False),
        sa.Column("event_id", sa.String(length=64), nullable=True),
        sa.Column("event_type", sa.String(length=32), nullable=True),
        sa.Column("alert_type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False, server_default="medium"),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_twin_alerts_id"), "twin_alerts", ["id"], unique=False)
    op.create_index(op.f("ix_twin_alerts_timestamp"), "twin_alerts", ["timestamp"], unique=False)
    op.create_index(op.f("ix_twin_alerts_device_id"), "twin_alerts", ["device_id"], unique=False)
    op.create_index(op.f("ix_twin_alerts_alert_type"), "twin_alerts", ["alert_type"], unique=False)
    op.create_index("ix_twin_alerts_type_ts", "twin_alerts", ["alert_type", "timestamp"], unique=False)
    op.create_index("ix_twin_alerts_device_ts", "twin_alerts", ["device_id", "timestamp"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_twin_alerts_device_ts", table_name="twin_alerts")
    op.drop_index("ix_twin_alerts_type_ts", table_name="twin_alerts")
    op.drop_index(op.f("ix_twin_alerts_alert_type"), table_name="twin_alerts")
    op.drop_index(op.f("ix_twin_alerts_device_id"), table_name="twin_alerts")
    op.drop_index(op.f("ix_twin_alerts_timestamp"), table_name="twin_alerts")
    op.drop_index(op.f("ix_twin_alerts_id"), table_name="twin_alerts")
    op.drop_table("twin_alerts")
