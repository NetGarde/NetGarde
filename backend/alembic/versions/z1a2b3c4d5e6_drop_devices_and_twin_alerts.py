"""drop_devices_and_twin_alerts

Revision ID: z1a2b3c4d5e6
Revises: y0z1a2b3c4d5
Create Date: 2026-07-16 14:20:00.000000

Drop remaining Postgres identity/alert tables. Live agent state stays in
Redis (twin:*); durable device rows and twin_alerts are removed.
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "z1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "y0z1a2b3c4d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    for table in ("twin_alerts", "devices"):
        connection.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))


def downgrade() -> None:
    raise NotImplementedError("Downgrade is intentionally unsupported for this cleanup migration.")
