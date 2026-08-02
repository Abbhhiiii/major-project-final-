"""Add organization ownership to videos and incidents."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("videos") as batch:
        batch.add_column(sa.Column("organization_id", sa.String(36), nullable=True))
        batch.create_index("ix_videos_organization_id", ["organization_id"])
    with op.batch_alter_table("incidents") as batch:
        batch.add_column(sa.Column("organization_id", sa.String(36), nullable=True))
        batch.create_index("ix_incidents_organization_id", ["organization_id"])


def downgrade() -> None:
    with op.batch_alter_table("incidents") as batch:
        batch.drop_index("ix_incidents_organization_id")
        batch.drop_column("organization_id")
    with op.batch_alter_table("videos") as batch:
        batch.drop_index("ix_videos_organization_id")
        batch.drop_column("organization_id")
