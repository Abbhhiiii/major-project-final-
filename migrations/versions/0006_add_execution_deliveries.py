"""Add execution delivery records."""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    op.create_table("deliveries", sa.Column("delivery_id", sa.String(36), primary_key=True), sa.Column("detection_id", sa.String(36), nullable=False), sa.Column("action_kind", sa.String(30), nullable=False), sa.Column("target", sa.String(255), nullable=False), sa.Column("status", sa.String(30), nullable=False), sa.Column("message", sa.String(1000), nullable=False), sa.Column("provider_reference", sa.String(100), nullable=False), sa.Column("report_path", sa.String(1000), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_deliveries_detection_id", "deliveries", ["detection_id"])

def downgrade() -> None:
    op.drop_table("deliveries")
