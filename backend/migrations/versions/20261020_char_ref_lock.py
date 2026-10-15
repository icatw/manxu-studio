"""add character reference_locked flag"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261020_char_ref_lock"
down_revision: str | None = "20261019_durable_image_tasks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "characters",
        sa.Column(
            "reference_locked",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("characters", "reference_locked")
