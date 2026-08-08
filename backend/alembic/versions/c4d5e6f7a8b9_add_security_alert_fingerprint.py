"""add fingerprint to security_alerts

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-07-16 22:40:00.000000

Idempotent detection alerts: a unique fingerprint prevents duplicate rows
when the engine re-evaluates the same event chain or Kafka replays messages.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, Sequence[str], None] = "b3c4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("security_alerts", sa.Column("fingerprint", sa.String(length=64), nullable=True))
    op.create_index(
        "ix_security_alerts_fingerprint",
        "security_alerts",
        ["fingerprint"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_security_alerts_fingerprint", table_name="security_alerts")
    op.drop_column("security_alerts", "fingerprint")
