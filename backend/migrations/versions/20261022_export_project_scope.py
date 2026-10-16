"""nullable episode_id and project_id on exports for anthology"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261022_export_project_scope"
down_revision: str | None = "20261021_serial_layer"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "exports",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "exports_project_id_fkey",
        "exports",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.alter_column(
        "exports",
        "episode_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.create_index("exports_project_idx", "exports", ["project_id"])
    # Backfill project_id from episode for existing rows.
    op.execute(
        """
        UPDATE exports AS e
        SET project_id = ep.project_id
        FROM episodes AS ep
        WHERE e.episode_id = ep.id AND e.project_id IS NULL
        """
    )
    op.alter_column(
        "exports",
        "project_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )


def downgrade() -> None:
    op.execute("DELETE FROM exports WHERE episode_id IS NULL")
    op.alter_column(
        "exports",
        "episode_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.drop_index("exports_project_idx", table_name="exports")
    op.drop_constraint("exports_project_id_fkey", "exports", type_="foreignkey")
    op.drop_column("exports", "project_id")
