"""add scoped idempotency keys to generation tasks"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261018_task_idempotency"
down_revision: str | None = "20261017_require_project_owner"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("generation_tasks", sa.Column("idempotency_key", sa.String(length=128), nullable=True))
    op.create_unique_constraint(
        "generation_tasks_owner_idempotency_key_uq",
        "generation_tasks",
        ["owner_id", "idempotency_key"],
    )


def downgrade() -> None:
    op.drop_constraint("generation_tasks_owner_idempotency_key_uq", "generation_tasks", type_="unique")
    op.drop_column("generation_tasks", "idempotency_key")
