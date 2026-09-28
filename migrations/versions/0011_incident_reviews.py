"""Persist operator corrections without overwriting original decisions."""
import sqlalchemy as sa
from alembic import op

revision = "0011_incident_reviews"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("incident_reviews",
        sa.Column("incident_id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False, index=True),
        sa.Column("reviewer_id", sa.String(36), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("response_action", sa.String(16), nullable=False),
        sa.Column("reason", sa.String(2000), nullable=False),
        sa.Column("false_alarm", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.String(50), nullable=False))


def downgrade():
    op.drop_table("incident_reviews")
