"""add_agents_table

Revision ID: a1b2c3d4e5f6
Revises: z1a2b3c4d5e6
Create Date: 2026-07-16 14:40:00.000000

Durable registry of TrustEdge Agent installs. Primary identity is agent_id
(same as the agent's local device_id); hostname is mutable metadata.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "z1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.String(length=128), nullable=False),
        sa.Column("hostname", sa.String(length=255), nullable=True),
        sa.Column("os", sa.String(length=64), nullable=True),
        sa.Column("os_version", sa.String(length=128), nullable=True),
        sa.Column("arch", sa.String(length=64), nullable=True),
        sa.Column("agent_version", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="registered"),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_id", name="uq_agents_agent_id"),
    )
    op.create_index("ix_agents_id", "agents", ["id"], unique=False)
    op.create_index("ix_agents_agent_id", "agents", ["agent_id"], unique=False)
    op.create_index("ix_agents_hostname", "agents", ["hostname"], unique=False)
    op.create_index("ix_agents_last_seen_at", "agents", ["last_seen_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_agents_last_seen_at", table_name="agents")
    op.drop_index("ix_agents_hostname", table_name="agents")
    op.drop_index("ix_agents_agent_id", table_name="agents")
    op.drop_index("ix_agents_id", table_name="agents")
    op.drop_table("agents")
