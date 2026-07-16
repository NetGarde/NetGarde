"""remove_vpn_and_refactor_devices

Revision ID: w8x9y0z1a2b3
Revises: v7w8x9y0z1a2
Create Date: 2026-07-16 13:00:00.000000

Remove WireGuard VPN tables (ip_pools, ip_leases, vpn_peers, vpn_enroll_events,
device_usage_samples) and reshape devices to use agent external_id identity.
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "w8x9y0z1a2b3"
down_revision: Union[str, Sequence[str], None] = "v7w8x9y0z1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()

    # --- Reshape devices while lease/peer tables still exist ---
    connection.execute(
        text(
            """
            ALTER TABLE devices
            ADD COLUMN IF NOT EXISTS external_id VARCHAR(128)
            """
        )
    )
    connection.execute(
        text(
            """
            ALTER TABLE devices
            ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ
            """
        )
    )

    # Backfill from VPN peer device_id when lease chain exists
    connection.execute(
        text(
            """
            UPDATE devices AS d
            SET external_id = vp.device_id
            FROM ip_leases AS il
            JOIN vpn_peers AS vp ON vp.id = il.peer_id
            WHERE d.ip_lease_id = il.id
              AND (d.external_id IS NULL OR d.external_id = '')
            """
        )
    )
    connection.execute(
        text(
            """
            UPDATE devices
            SET external_id = 'legacy-' || id::text
            WHERE external_id IS NULL OR external_id = ''
            """
        )
    )
    connection.execute(text("ALTER TABLE devices ALTER COLUMN external_id SET NOT NULL"))
    connection.execute(
        text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS ix_devices_external_id
            ON devices (external_id)
            """
        )
    )

    # Login geo no longer references vpn_peers
    connection.execute(
        text(
            """
            ALTER TABLE device_login_geo_observations
            DROP CONSTRAINT IF EXISTS device_login_geo_observations_peer_id_fkey
            """
        )
    )
    connection.execute(
        text(
            """
            ALTER TABLE device_login_geo_observations
            DROP COLUMN IF EXISTS peer_id
            """
        )
    )

    connection.execute(text("DROP TABLE IF EXISTS vpn_enroll_events CASCADE"))
    connection.execute(text("DROP TABLE IF EXISTS device_usage_samples CASCADE"))

    connection.execute(
        text("ALTER TABLE devices DROP CONSTRAINT IF EXISTS fk_devices_ip_lease_id_ip_leases")
    )
    connection.execute(
        text("ALTER TABLE devices DROP CONSTRAINT IF EXISTS uq_devices_ip_lease_id")
    )
    connection.execute(text("DROP INDEX IF EXISTS ix_devices_ip_lease_id"))
    connection.execute(text("DROP INDEX IF EXISTS uq_devices_ip_lease_id"))
    connection.execute(text("ALTER TABLE devices DROP COLUMN IF EXISTS ip_lease_id"))

    connection.execute(text("DROP TABLE IF EXISTS ip_leases CASCADE"))
    connection.execute(text("DROP TABLE IF EXISTS vpn_peers CASCADE"))
    connection.execute(text("DROP TABLE IF EXISTS ip_pools CASCADE"))


def downgrade() -> None:
    raise NotImplementedError("Downgrade is intentionally unsupported for VPN removal.")
