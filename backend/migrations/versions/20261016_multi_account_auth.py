"""add multi-account identities and email login challenges"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261016_multi_account_auth"
down_revision: str | None = "20261015_account_settings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "UPDATE projects SET owner_id = account_registry.account_id "
        "FROM account_registry WHERE projects.owner_id IS NULL "
        "AND account_registry.id = 1 AND account_registry.account_id IS NOT NULL"
    )
    op.alter_column("accounts", "github_id", nullable=True)
    op.alter_column("accounts", "github_login", nullable=True)
    op.add_column("oauth_states", sa.Column("provider", sa.String(24), nullable=True))
    op.add_column("oauth_states", sa.Column("intent", sa.String(24), nullable=True))
    op.execute("UPDATE oauth_states SET provider = 'github', intent = 'login'")
    op.alter_column("oauth_states", "provider", nullable=False)
    op.alter_column("oauth_states", "intent", nullable=False)
    op.create_table(
        "auth_identities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(24), nullable=False),
        sa.Column("provider_subject", sa.String(240), nullable=False),
        sa.Column("email_original", sa.String(320)),
        sa.Column("email_normalized", sa.String(320)),
        sa.Column("email_verified_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "auth_identities_provider_subject_idx",
        "auth_identities",
        ["provider", "provider_subject"],
        unique=True,
    )
    op.create_index("auth_identities_account_idx", "auth_identities", ["account_id"])
    op.add_column(
        "generation_tasks",
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.execute(
        "UPDATE generation_tasks SET owner_id = projects.owner_id "
        "FROM projects WHERE generation_tasks.project_id = projects.id"
    )
    op.alter_column("generation_tasks", "owner_id", nullable=False)
    op.create_foreign_key(
        "generation_tasks_owner_id_fkey",
        "generation_tasks",
        "accounts",
        ["owner_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_table(
        "email_login_challenges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email_normalized", sa.String(320), nullable=False),
        sa.Column("code_digest", sa.String(128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "last_sent_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "email_challenges_email_created_idx",
        "email_login_challenges",
        ["email_normalized", "created_at"],
    )
    connection = op.get_bind()
    accounts = connection.execute(
        sa.text("SELECT id, github_id, created_at FROM accounts WHERE github_id IS NOT NULL")
    )
    for account_id, github_id, created_at in accounts:
        connection.execute(
            sa.text(
                "INSERT INTO auth_identities "
                "(id, account_id, provider, provider_subject, created_at) "
                "VALUES (:id, :account_id, 'github', :subject, :created_at)"
            ),
            {
                "id": uuid4(),
                "account_id": account_id,
                "subject": str(github_id),
                "created_at": created_at,
            },
        )


def downgrade() -> None:
    op.drop_constraint("generation_tasks_owner_id_fkey", "generation_tasks", type_="foreignkey")
    op.drop_column("generation_tasks", "owner_id")
    op.drop_index("email_challenges_email_created_idx", table_name="email_login_challenges")
    op.drop_table("email_login_challenges")
    op.drop_index("auth_identities_account_idx", table_name="auth_identities")
    op.drop_index("auth_identities_provider_subject_idx", table_name="auth_identities")
    op.drop_table("auth_identities")
    op.drop_column("oauth_states", "intent")
    op.drop_column("oauth_states", "provider")
    op.alter_column("accounts", "github_login", nullable=False)
    op.alter_column("accounts", "github_id", nullable=False)
