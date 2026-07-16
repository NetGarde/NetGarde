"""drop_dns_legacy_tables

Revision ID: v7w8x9y0z1a2
Revises: u6v7w8x9y0z1
Create Date: 2026-07-16 12:00:00.000000

Drop DNS-era tables and policy sync infrastructure no longer used by the
endpoint security observability product.
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "v7w8x9y0z1a2"
down_revision: Union[str, Sequence[str], None] = "u6v7w8x9y0z1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()

    for table in ("devices", "policy_profiles", "policy_packs"):
        connection.execute(
            text(f"DROP TRIGGER IF EXISTS tr_{table}_policy_changed_notify ON {table}")
        )
    connection.execute(text("DROP FUNCTION IF EXISTS notify_policy_changed()"))

    connection.execute(text("DROP TABLE IF EXISTS dns_queries CASCADE"))
    connection.execute(text("DROP TABLE IF EXISTS domain_first_seen CASCADE"))
    connection.execute(text("DROP TABLE IF EXISTS policy_sync_status CASCADE"))
    connection.execute(text("DROP TABLE IF EXISTS geo_country_blocks CASCADE"))
    connection.execute(text("DROP TABLE IF EXISTS geo_country_policy_config CASCADE"))
    connection.execute(text("DROP TABLE IF EXISTS policy_packs CASCADE"))


def downgrade() -> None:
    raise NotImplementedError("Downgrade is intentionally unsupported for this cleanup migration.")
