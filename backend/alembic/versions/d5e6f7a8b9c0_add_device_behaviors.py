"""add_device_behaviors

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-07-25 18:00:00.000000

Per-device learned behavior counters used by detection-engine to suppress
repeated familiar patterns (baseline / frequency allowlisting).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d5e6f7a8b9c0"
down_revision: Union[str, Sequence[str], None] = "c4d5e6f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "device_behaviors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.String(length=128), nullable=False),
        sa.Column("behavior_kind", sa.String(length=64), nullable=False),
        sa.Column("behavior_key", sa.String(length=255), nullable=False),
        sa.Column("alert_type", sa.String(length=64), nullable=True),
        sa.Column("count", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_alert_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "device_id",
            "behavior_kind",
            "behavior_key",
            name="uq_device_behaviors_device_kind_key",
        ),
    )
    op.create_index("ix_device_behaviors_id", "device_behaviors", ["id"], unique=False)
    op.create_index("ix_device_behaviors_device_id", "device_behaviors", ["device_id"], unique=False)
    op.create_index(
        "ix_device_behaviors_device_count",
        "device_behaviors",
        ["device_id", "count"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_device_behaviors_device_count", table_name="device_behaviors")
    op.drop_index("ix_device_behaviors_device_id", table_name="device_behaviors")
    op.drop_index("ix_device_behaviors_id", table_name="device_behaviors")
    op.drop_table("device_behaviors")
