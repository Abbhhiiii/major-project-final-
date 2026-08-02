"""Add video catalog and incident source metadata."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = inspector.get_table_names()
    if "videos" not in tables:
        op.create_table(
            "videos",
            sa.Column("video_id", sa.String(length=36), nullable=False),
            sa.Column("original_filename", sa.String(length=255), nullable=False),
            sa.Column("stored_name", sa.String(length=255), nullable=False),
            sa.Column("content_type", sa.String(length=100), nullable=False),
            sa.Column("size_bytes", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("video_id"),
            sa.UniqueConstraint("stored_name"),
        )
        op.create_index("ix_videos_created_at", "videos", ["created_at"], unique=False)

    incident_columns = {column["name"] for column in inspector.get_columns("incidents")}
    if "source_video_id" not in incident_columns:
        op.add_column(
            "incidents", sa.Column("source_video_id", sa.String(length=36), nullable=True)
        )
    if "frame_timestamp_ms" not in incident_columns:
        op.add_column("incidents", sa.Column("frame_timestamp_ms", sa.Integer(), nullable=True))
    indexes = {index["name"] for index in inspector.get_indexes("incidents")}
    if "ix_incidents_source_video_id" not in indexes:
        op.create_index("ix_incidents_source_video_id", "incidents", ["source_video_id"])


def downgrade() -> None:
    op.drop_index("ix_incidents_source_video_id", table_name="incidents")
    op.drop_column("incidents", "frame_timestamp_ms")
    op.drop_column("incidents", "source_video_id")
    op.drop_index("ix_videos_created_at", table_name="videos")
    op.drop_table("videos")
