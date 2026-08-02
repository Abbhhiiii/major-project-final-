"""Preserve organization scope through background video processing."""

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("processing_jobs") as batch:
        batch.add_column(sa.Column("organization_id", sa.String(length=36), nullable=True))
        batch.create_index("ix_processing_jobs_organization_id", ["organization_id"])


def downgrade() -> None:
    with op.batch_alter_table("processing_jobs") as batch:
        batch.drop_index("ix_processing_jobs_organization_id")
        batch.drop_column("organization_id")
