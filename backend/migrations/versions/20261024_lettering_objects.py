"""lettering objects for LETTER A2"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261024_lettering_objects"
down_revision: str | None = "20261023_layout_pages"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "lettering_objects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("x_pct", sa.Float(), nullable=False, server_default="8"),
        sa.Column("y_pct", sa.Float(), nullable=False, server_default="6"),
        sa.Column("width_pct", sa.Float(), nullable=False, server_default="60"),
        sa.Column("tail", sa.String(length=32), nullable=False, server_default="bottom_left"),
        sa.Column("font_size", sa.String(length=8), nullable=False, server_default="md"),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
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
        sa.ForeignKeyConstraint(["slot_id"], ["page_slots.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "lettering_objects_slot_position_idx",
        "lettering_objects",
        ["slot_id", "position"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("lettering_objects_slot_position_idx", table_name="lettering_objects")
    op.drop_table("lettering_objects")
