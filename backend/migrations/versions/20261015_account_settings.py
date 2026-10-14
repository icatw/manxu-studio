"""add editable account profile and image endpoint"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261015_account_settings"
down_revision: str | None = "20261014_account_workbench"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("display_name", sa.String(80), nullable=True))
    op.add_column(
        "account_model_configs",
        sa.Column(
            "image_base_url",
            sa.Text(),
            nullable=False,
            server_default="https://dashscope.aliyuncs.com/api/v1",
        ),
    )


def downgrade() -> None:
    op.drop_column("account_model_configs", "image_base_url")
    op.drop_column("accounts", "display_name")
