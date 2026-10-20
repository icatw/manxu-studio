from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models_catalog import DEFAULT_IMAGE_MODEL
from app.db.base import Base


class ProjectRecord(Base):
    __tablename__ = "projects"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    synopsis: Mapped[str] = mapped_column(Text, nullable=False)
    genre: Mapped[str] = mapped_column(String(80), nullable=False)
    art_style: Mapped[str] = mapped_column(String(240), nullable=False)
    aspect_ratio: Mapped[str] = mapped_column(String(20), nullable=False)
    world_setting: Mapped[str] = mapped_column(Text, nullable=False, default="")
    style_rules: Mapped[str] = mapped_column(Text, nullable=False, default="")
    negative_prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    style_seed: Mapped[int | None] = mapped_column(Integer)
    cover_asset_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
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
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    panel_count: Mapped[int] = mapped_column(Integer, nullable=False, default=8)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PlotThreadRecord(Base):
    __tablename__ = "plot_threads"
    __table_args__ = (Index("plot_threads_project_idx", "project_id"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    planted_in_episode_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("episodes.id", ondelete="SET NULL")
    )
    payoff_in_episode_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("episodes.id", ondelete="SET NULL")
    )
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
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
    reference_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


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


class LayoutPageRecord(Base):
    __tablename__ = "layout_pages"
    __table_args__ = (
        Index("layout_pages_episode_position_idx", "episode_id", "position", unique=True),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    episode_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    template: Mapped[str] = mapped_column(String(32), nullable=False, default="vertical_strip")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PageSlotRecord(Base):
    __tablename__ = "page_slots"
    __table_args__ = (
        Index("page_slots_page_position_idx", "page_id", "position", unique=True),
        Index("page_slots_panel_idx", "panel_id"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    page_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("layout_pages.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    panel_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("storyboard_panels.id", ondelete="CASCADE"), nullable=False
    )
    image_version_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("panel_image_versions.id", ondelete="SET NULL")
    )
    height_px: Mapped[int] = mapped_column(Integer, nullable=False, default=720)
    gap_after_px: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    follow_current_version: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class LetteringObjectRecord(Base):
    __tablename__ = "lettering_objects"
    __table_args__ = (
        Index("lettering_objects_slot_position_idx", "slot_id", "position", unique=True),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    slot_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("page_slots.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    x_pct: Mapped[float] = mapped_column(Float, nullable=False, default=8.0)
    y_pct: Mapped[float] = mapped_column(Float, nullable=False, default=6.0)
    width_pct: Mapped[float] = mapped_column(Float, nullable=False, default=60.0)
    tail: Mapped[str] = mapped_column(String(32), nullable=False, default="bottom_left")
    font_size: Mapped[str] = mapped_column(String(8), nullable=False, default="md")
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class GenerationTaskRecord(Base):
    __tablename__ = "generation_tasks"
    __table_args__ = (
        Index("generation_tasks_created_idx", "created_at"),
        UniqueConstraint(
            "owner_id", "idempotency_key", name="generation_tasks_owner_idempotency_key_uq"
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
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
    idempotency_key: Mapped[str | None] = mapped_column(String(128))
    result: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    error: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    retry_of_task_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class UsageEventRecord(Base):
    __tablename__ = "usage_events"
    __table_args__ = (
        Index("usage_events_account_created_idx", "account_id", "created_at"),
        Index("usage_events_generation_task_idx", "generation_task_id"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL")
    )
    generation_task_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("generation_tasks.id", ondelete="SET NULL")
    )
    request_id: Mapped[str | None] = mapped_column(String(64))
    call_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)
    total_tokens: Mapped[int | None] = mapped_column(Integer)
    image_units: Mapped[int | None] = mapped_column(Integer)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    billable: Mapped[bool] = mapped_column(Boolean, nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ExportRecord(Base):
    __tablename__ = "exports"
    __table_args__ = (Index("exports_project_idx", "project_id"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    episode_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("episodes.id", ondelete="CASCADE"), nullable=True
    )
    format: Mapped[str] = mapped_column(String(24), nullable=False)
    filename: Mapped[str] = mapped_column(String(160), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AccountRecord(Base):
    __tablename__ = "accounts"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    github_id: Mapped[int | None] = mapped_column(Integer, unique=True)
    github_login: Mapped[str | None] = mapped_column(String(120))
    display_name: Mapped[str | None] = mapped_column(String(80))
    avatar_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AccountRegistryRecord(Base):
    __tablename__ = "account_registry"
    __table_args__ = (CheckConstraint("id = 1", name="account_registry_singleton"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("accounts.id"))


class OAuthStateRecord(Base):
    __tablename__ = "oauth_states"

    state_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider: Mapped[str] = mapped_column(String(24), nullable=False, default="github")
    intent: Mapped[str] = mapped_column(String(24), nullable=False, default="login")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AccountSessionRecord(Base):
    __tablename__ = "account_sessions"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuthIdentityRecord(Base):
    __tablename__ = "auth_identities"
    __table_args__ = (
        Index("auth_identities_provider_subject_idx", "provider", "provider_subject", unique=True),
        Index("auth_identities_account_idx", "account_id"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(24), nullable=False)
    provider_subject: Mapped[str] = mapped_column(String(240), nullable=False)
    email_original: Mapped[str | None] = mapped_column(String(320))
    email_normalized: Mapped[str | None] = mapped_column(String(320))
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EmailLoginChallengeRecord(Base):
    __tablename__ = "email_login_challenges"
    __table_args__ = (
        Index("email_challenges_email_created_idx", "email_normalized", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    email_normalized: Mapped[str] = mapped_column(String(320), nullable=False)
    code_digest: Mapped[str] = mapped_column(String(128), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class AccountModelConfigRecord(Base):
    __tablename__ = "account_model_configs"

    account_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), primary_key=True
    )
    text_model: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    text_base_url: Mapped[str] = mapped_column(Text, nullable=False, default="")
    text_api_key_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary)
    image_model: Mapped[str] = mapped_column(
        String(80), nullable=False, default=DEFAULT_IMAGE_MODEL
    )
    image_backend: Mapped[str] = mapped_column(String(32), nullable=False, default="qwen_async")
    image_base_url: Mapped[str] = mapped_column(
        Text, nullable=False, default="https://dashscope.aliyuncs.com/api/v1"
    )
    image_api_key_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary)
    text_status: Mapped[str] = mapped_column(String(24), nullable=False, default="not_configured")
    image_status: Mapped[str] = mapped_column(String(24), nullable=False, default="not_configured")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
