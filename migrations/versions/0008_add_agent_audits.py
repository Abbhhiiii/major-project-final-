"""Add durable RAG, reasoning, planning, and execution audit records."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_audits",
        sa.Column("audit_id", sa.String(36), primary_key=True),
        sa.Column("incident_id", sa.String(36), nullable=False),
        sa.Column("detection_id", sa.String(36), nullable=False),
        sa.Column("reasoning_provider", sa.String(50), nullable=False),
        sa.Column("reasoning_model", sa.String(100), nullable=False),
        sa.Column("retrieval", sa.JSON(), nullable=False),
        sa.Column("decision", sa.JSON(), nullable=False),
        sa.Column("plan", sa.JSON(), nullable=False),
        sa.Column("execution", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agent_audits_incident_id", "agent_audits", ["incident_id"], unique=True)
    op.create_index("ix_agent_audits_detection_id", "agent_audits", ["detection_id"])


def downgrade() -> None:
    op.drop_table("agent_audits")
