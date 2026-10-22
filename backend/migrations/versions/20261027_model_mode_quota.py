"""account model_mode + usage_events.billing_source"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261027_model_mode_quota"
down_revision: str | None = "20261026_usage_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "account_model_configs",
        sa.Column(
            "model_mode",
            sa.String(length=24),
            nullable=False,
            server_default="byok_qwen",
        ),
    )
    op.add_column(
        "usage_events",
        sa.Column(
            "billing_source",
            sa.String(length=16),
            nullable=False,
            server_default="byok",
        ),
    )
    op.create_index(
        "usage_events_account_billing_created_idx",
        "usage_events",
        ["account_id", "billing_source", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("usage_events_account_billing_created_idx", table_name="usage_events")
    op.drop_column("usage_events", "billing_source")
    op.drop_column("account_model_configs", "model_mode")
