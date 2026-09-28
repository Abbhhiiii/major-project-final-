"""Persist the learned verification baseline by organization and location."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "learned_threshold_profiles",
        sa.Column("profile_key", sa.String(64), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("location", sa.String(255), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("applied_review_versions", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_learned_threshold_profiles_organization_id",
        "learned_threshold_profiles",
        ["organization_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_learned_threshold_profiles_organization_id",
        table_name="learned_threshold_profiles",
    )
    op.drop_table("learned_threshold_profiles")
