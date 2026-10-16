"""layout pages and page slots for PAGE A1"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261023_layout_pages"
down_revision: str | None = "20261022_export_project_scope"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "layout_pages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("episode_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "template", sa.String(length=32), nullable=False, server_default="vertical_strip"
        ),
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
        sa.ForeignKeyConstraint(["episode_id"], ["episodes.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "layout_pages_episode_position_idx",
        "layout_pages",
        ["episode_id", "position"],
        unique=True,
    )

    op.create_table(
        "page_slots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("page_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("panel_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("image_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("height_px", sa.Integer(), nullable=False, server_default="720"),
        sa.Column("gap_after_px", sa.Integer(), nullable=False, server_default="24"),
        sa.Column(
            "follow_current_version", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
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
        sa.ForeignKeyConstraint(["page_id"], ["layout_pages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["panel_id"], ["storyboard_panels.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["image_version_id"], ["panel_image_versions.id"], ondelete="SET NULL"
        ),
    )
    op.create_index(
        "page_slots_page_position_idx", "page_slots", ["page_id", "position"], unique=True
    )
    op.create_index("page_slots_panel_idx", "page_slots", ["panel_id"])


def downgrade() -> None:
    op.drop_index("page_slots_panel_idx", table_name="page_slots")
    op.drop_index("page_slots_page_position_idx", table_name="page_slots")
    op.drop_table("page_slots")
    op.drop_index("layout_pages_episode_position_idx", table_name="layout_pages")
    op.drop_table("layout_pages")
