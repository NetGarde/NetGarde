"""drop_legacy_dns_behavior_tables

Revision ID: x9y0z1a2b3c4
Revises: w8x9y0z1a2b3
Create Date: 2026-07-16 14:00:00.000000

Drop remaining DNS-era / VPN-enroll-era tables no longer used by the
endpoint security product. Detection alerts live in twin_alerts.
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "x9y0z1a2b3c4"
down_revision: Union[str, Sequence[str], None] = "w8x9y0z1a2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    for table in (
        "dns_alerts",
        "client_blocked_domains",
        "device_security_policies",
        "client_behavior_profiles",
        "client_behavior_rollups",
        "device_country_presences",
        "device_login_geo_observations",
    ):
        connection.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))


def downgrade() -> None:
    raise NotImplementedError("Downgrade is intentionally unsupported for this cleanup migration.")
