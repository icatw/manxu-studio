"""project bible, episode summary, plot threads"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261021_serial_layer"
down_revision: str | None = "20261020_char_ref_lock"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("world_setting", sa.Text(), server_default="", nullable=False),
    )
    op.add_column(
        "projects",
        sa.Column("style_rules", sa.Text(), server_default="", nullable=False),
    )
    op.add_column(
        "projects",
        sa.Column("negative_prompt", sa.Text(), server_default="", nullable=False),
    )
    op.add_column("projects", sa.Column("style_seed", sa.Integer(), nullable=True))
    op.add_column(
        "projects",
        sa.Column("cover_asset_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "episodes",
        sa.Column("summary", sa.Text(), server_default="", nullable=False),
    )
    op.create_table(
        "plot_threads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "planted_in_episode_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("episodes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "payoff_in_episode_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("episodes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("resolved", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("plot_threads_project_idx", "plot_threads", ["project_id"])


def downgrade() -> None:
    op.drop_index("plot_threads_project_idx", table_name="plot_threads")
    op.drop_table("plot_threads")
    op.drop_column("episodes", "summary")
    op.drop_column("projects", "cover_asset_id")
    op.drop_column("projects", "style_seed")
    op.drop_column("projects", "negative_prompt")
    op.drop_column("projects", "style_rules")
    op.drop_column("projects", "world_setting")
