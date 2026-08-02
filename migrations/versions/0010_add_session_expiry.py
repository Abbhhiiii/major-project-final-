"""Add creation and expiration timestamps to authentication sessions."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("auth_sessions") as batch:
        batch.add_column(sa.Column("created_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE auth_sessions SET created_at = CURRENT_TIMESTAMP, expires_at = datetime(CURRENT_TIMESTAMP, '+12 hours')")
    with op.batch_alter_table("auth_sessions") as batch:
        batch.alter_column("created_at", nullable=False)
        batch.alter_column("expires_at", nullable=False)
        batch.create_index("ix_auth_sessions_expires_at", ["expires_at"])


def downgrade() -> None:
    with op.batch_alter_table("auth_sessions") as batch:
        batch.drop_index("ix_auth_sessions_expires_at")
        batch.drop_column("expires_at")
        batch.drop_column("created_at")
