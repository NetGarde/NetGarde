"""rename twin_alerts to security_alerts

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-07-16 22:10:00.000000

Drop legacy TrustTwin naming for detection alerts.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, Sequence[str], None] = "a2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.rename_table("twin_alerts", "security_alerts")
    op.execute("ALTER INDEX IF EXISTS ix_twin_alerts_id RENAME TO ix_security_alerts_id")
    op.execute(
        "ALTER INDEX IF EXISTS ix_twin_alerts_timestamp RENAME TO ix_security_alerts_timestamp"
    )
    op.execute(
        "ALTER INDEX IF EXISTS ix_twin_alerts_device_id RENAME TO ix_security_alerts_device_id"
    )
    op.execute(
        "ALTER INDEX IF EXISTS ix_twin_alerts_alert_type RENAME TO ix_security_alerts_alert_type"
    )
    op.execute("ALTER INDEX IF EXISTS ix_twin_alerts_type_ts RENAME TO ix_security_alerts_type_ts")
    op.execute(
        "ALTER INDEX IF EXISTS ix_twin_alerts_device_ts RENAME TO ix_security_alerts_device_ts"
    )


def downgrade() -> None:
    op.execute(
        "ALTER INDEX IF EXISTS ix_security_alerts_device_ts RENAME TO ix_twin_alerts_device_ts"
    )
    op.execute("ALTER INDEX IF EXISTS ix_security_alerts_type_ts RENAME TO ix_twin_alerts_type_ts")
    op.execute(
        "ALTER INDEX IF EXISTS ix_security_alerts_alert_type RENAME TO ix_twin_alerts_alert_type"
    )
    op.execute(
        "ALTER INDEX IF EXISTS ix_security_alerts_device_id RENAME TO ix_twin_alerts_device_id"
    )
    op.execute(
        "ALTER INDEX IF EXISTS ix_security_alerts_timestamp RENAME TO ix_twin_alerts_timestamp"
    )
    op.execute("ALTER INDEX IF EXISTS ix_security_alerts_id RENAME TO ix_twin_alerts_id")
    op.rename_table("security_alerts", "twin_alerts")
