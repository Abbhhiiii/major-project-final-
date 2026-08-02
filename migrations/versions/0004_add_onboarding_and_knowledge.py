"""Add mock authentication, onboarding, and policy knowledge tables."""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    op.create_table("organizations", sa.Column("organization_id", sa.String(36), primary_key=True), sa.Column("name", sa.String(255), nullable=False), sa.Column("emergency_contact", sa.String(255), nullable=False), sa.Column("notification_preference", sa.String(100), nullable=False), sa.Column("api_key_last_four", sa.String(4), nullable=False), sa.Column("api_key_fingerprint", sa.String(64), nullable=False))
    op.create_table("users", sa.Column("user_id", sa.String(36), primary_key=True), sa.Column("organization_id", sa.String(36), nullable=False), sa.Column("email", sa.String(320), nullable=False, unique=True), sa.Column("password_hash", sa.String(200), nullable=False))
    op.create_index("ix_users_organization_id", "users", ["organization_id"])
    op.create_table("auth_sessions", sa.Column("token_hash", sa.String(64), primary_key=True), sa.Column("user_id", sa.String(36), nullable=False), sa.Column("organization_id", sa.String(36), nullable=False))
    op.create_table("cameras", sa.Column("camera_id", sa.String(36), primary_key=True), sa.Column("organization_id", sa.String(36), nullable=False), sa.Column("name", sa.String(255), nullable=False), sa.Column("location", sa.String(255), nullable=False))
    op.create_index("ix_cameras_organization_id", "cameras", ["organization_id"])
    op.create_table("knowledge_documents", sa.Column("document_id", sa.String(36), primary_key=True), sa.Column("organization_id", sa.String(36), nullable=False), sa.Column("filename", sa.String(255), nullable=False), sa.Column("stored_name", sa.String(255), nullable=False), sa.Column("page_count", sa.Integer(), nullable=False), sa.Column("chunk_count", sa.Integer(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_knowledge_documents_organization_id", "knowledge_documents", ["organization_id"])
    op.create_table("knowledge_chunks", sa.Column("chunk_id", sa.Integer(), primary_key=True, autoincrement=True), sa.Column("document_id", sa.String(36), nullable=False), sa.Column("organization_id", sa.String(36), nullable=False), sa.Column("position", sa.Integer(), nullable=False), sa.Column("content", sa.String(), nullable=False))
    op.create_index("ix_knowledge_chunks_document_id", "knowledge_chunks", ["document_id"])
    op.create_index("ix_knowledge_chunks_organization_id", "knowledge_chunks", ["organization_id"])

def downgrade() -> None:
    for table in ("knowledge_chunks", "knowledge_documents", "cameras", "auth_sessions", "users", "organizations"):
        op.drop_table(table)
