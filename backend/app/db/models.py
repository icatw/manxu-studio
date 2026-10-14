from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, LargeBinary, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProjectRecord(Base):
    __tablename__ = "projects"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    synopsis: Mapped[str] = mapped_column(Text, nullable=False)
    genre: Mapped[str] = mapped_column(String(80), nullable=False)
    art_style: Mapped[str] = mapped_column(String(240), nullable=False)
    aspect_ratio: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class EpisodeRecord(Base):
    __tablename__ = "episodes"
    __table_args__ = (
        Index("episodes_project_position_idx", "project_id", "position", unique=True),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    synopsis: Mapped[str] = mapped_column(Text, nullable=False)
    panel_count: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CharacterRecord(Base):
    __tablename__ = "characters"
    __table_args__ = (Index("characters_project_idx", "project_id"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    profile: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    reference_asset_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))


class SceneRecord(Base):
    __tablename__ = "scenes"
    __table_args__ = (Index("scenes_project_idx", "project_id"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    profile: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    reference_asset_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))


class PanelRecord(Base):
    __tablename__ = "storyboard_panels"
    __table_args__ = (Index("panels_episode_position_idx", "episode_id", "position", unique=True),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    episode_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    scene_description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    shot: Mapped[str] = mapped_column(String(240), nullable=False, default="中景")
    composition: Mapped[str] = mapped_column(Text, nullable=False, default="")
    character_actions: Mapped[str] = mapped_column(Text, nullable=False, default="")
    emotion: Mapped[str] = mapped_column(String(240), nullable=False, default="")
    dialogue: Mapped[str] = mapped_column(Text, nullable=False, default="")
    story_purpose: Mapped[str] = mapped_column(Text, nullable=False, default="")
    image_prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    character_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    scene_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    review_status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    current_image_asset_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    current_image_url: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ImageVersionRecord(Base):
    __tablename__ = "panel_image_versions"
    __table_args__ = (Index("image_versions_panel_created_idx", "panel_id", "created_at"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    panel_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("storyboard_panels.id", ondelete="CASCADE"), nullable=False
    )
    asset_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, default=uuid4)
    image_url: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class GenerationTaskRecord(Base):
    __tablename__ = "generation_tasks"
    __table_args__ = (Index("generation_tasks_created_idx", "created_at"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    episode_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("episodes.id", ondelete="CASCADE")
    )
    panel_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("storyboard_panels.id", ondelete="CASCADE")
    )
    task_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")
    progress: Mapped[int | None] = mapped_column(Integer)
    request_data: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    result: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    error: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    retry_of_task_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ExportRecord(Base):
    __tablename__ = "exports"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    episode_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False
    )
    format: Mapped[str] = mapped_column(String(24), nullable=False)
    filename: Mapped[str] = mapped_column(String(160), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
