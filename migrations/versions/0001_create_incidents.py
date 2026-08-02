"""Create incident memory table."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if "incidents" in sa.inspect(op.get_bind()).get_table_names():
        # Adopt databases created by the original zero-setup demo bootstrap.
        return
    op.create_table(
        "incidents",
        sa.Column("incident_id", sa.String(length=36), nullable=False),
        sa.Column("detection_id", sa.String(length=36), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=False),
        sa.Column("rationale", sa.JSON(), nullable=False),
        sa.Column("alert_message", sa.String(length=1000), nullable=False),
        sa.Column("stored_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("incident_id"),
    )
    op.create_index("ix_incidents_detection_id", "incidents", ["detection_id"], unique=True)
    op.create_index("ix_incidents_severity", "incidents", ["severity"], unique=False)
    op.create_index("ix_incidents_stored_at", "incidents", ["stored_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_incidents_stored_at", table_name="incidents")
    op.drop_index("ix_incidents_severity", table_name="incidents")
    op.drop_index("ix_incidents_detection_id", table_name="incidents")
    op.drop_table("incidents")
