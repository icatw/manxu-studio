"""add single-account GitHub auth and model settings"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261014_account_workbench"
down_revision: str | None = "c555e7bbdaea"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("github_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("github_login", sa.String(120), nullable=False),
        sa.Column("avatar_url", sa.Text()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_table(
        "account_registry",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("accounts.id")),
        sa.CheckConstraint("id = 1", name="account_registry_singleton"),
    )
    op.execute("INSERT INTO account_registry (id, account_id) VALUES (1, NULL)")
    op.create_table(
        "oauth_states",
        sa.Column("state_hash", sa.String(64), primary_key=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "account_sessions",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column(
            "account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_table(
        "account_model_configs",
        sa.Column(
            "account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("text_model", sa.String(160), nullable=False, server_default=""),
        sa.Column("text_base_url", sa.Text(), nullable=False, server_default=""),
        sa.Column("text_api_key_encrypted", sa.LargeBinary()),
        sa.Column(
            "image_model", sa.String(80), nullable=False, server_default="qwen-image-3.0-pro"
        ),
        sa.Column("image_api_key_encrypted", sa.LargeBinary()),
        sa.Column("text_status", sa.String(24), nullable=False, server_default="not_configured"),
        sa.Column("image_status", sa.String(24), nullable=False, server_default="not_configured"),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.add_column("projects", sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("projects_owner_id_fkey", "projects", "accounts", ["owner_id"], ["id"])
    op.create_index("projects_owner_created_idx", "projects", ["owner_id", "created_at"])


def downgrade() -> None:
    op.drop_index("projects_owner_created_idx", table_name="projects")
    op.drop_constraint("projects_owner_id_fkey", "projects", type_="foreignkey")
    op.drop_column("projects", "owner_id")
    op.drop_table("account_model_configs")
    op.drop_table("account_sessions")
    op.drop_table("oauth_states")
    op.drop_table("account_registry")
    op.drop_table("accounts")
