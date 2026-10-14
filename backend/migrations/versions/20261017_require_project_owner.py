"""require every project to have an owner"""

from collections.abc import Sequence

from alembic import op

revision: str = "20261017_require_project_owner"
down_revision: str | None = "20261016_multi_account_auth"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("projects", "owner_id", nullable=False)


def downgrade() -> None:
    op.alter_column("projects", "owner_id", nullable=True)
