"""Store the latest generated sensor-twin frame on processing jobs."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: str | None = "0011_incident_reviews"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("processing_jobs") as batch:
        batch.add_column(
            sa.Column("sensor_scenario", sa.String(100), nullable=False, server_default="")
        )
        batch.add_column(sa.Column("latest_sensor_sample", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("processing_jobs") as batch:
        batch.drop_column("latest_sensor_sample")
        batch.drop_column("sensor_scenario")
