"""account model config image_backend"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261025_image_backend"
down_revision: str | None = "20261024_lettering_objects"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "account_model_configs",
        sa.Column(
            "image_backend",
            sa.String(length=32),
            nullable=False,
            server_default="qwen_async",
        ),
    )


def downgrade() -> None:
    op.drop_column("account_model_configs", "image_backend")
