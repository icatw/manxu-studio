"""usage_events ledger for provider call metering"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261026_usage_events"
down_revision: str | None = "20261025_image_backend"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "usage_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("generation_task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("call_kind", sa.String(length=16), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("image_units", sa.Integer(), nullable=True),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("billable", sa.Boolean(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["generation_task_id"], ["generation_tasks.id"], ondelete="SET NULL"
        ),
    )
    op.create_index(
        "usage_events_account_created_idx",
        "usage_events",
        ["account_id", "created_at"],
    )
    op.create_index(
        "usage_events_generation_task_idx",
        "usage_events",
        ["generation_task_id"],
    )


def downgrade() -> None:
    op.drop_index("usage_events_generation_task_idx", table_name="usage_events")
    op.drop_index("usage_events_account_created_idx", table_name="usage_events")
    op.drop_table("usage_events")
