from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class APIModel(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class ProjectCreate(APIModel):
    title: str = Field(min_length=1, max_length=120)
    synopsis: str = Field(min_length=1, max_length=10000)
    genre: str = Field(min_length=1, max_length=80)
    art_style: str = Field(min_length=1, max_length=240)
    aspect_ratio: Literal["portrait", "landscape", "square"]


class ProjectPatch(APIModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    synopsis: str | None = Field(default=None, min_length=1, max_length=10000)
    genre: str | None = Field(default=None, min_length=1, max_length=80)
    art_style: str | None = Field(default=None, min_length=1, max_length=240)
    aspect_ratio: Literal["portrait", "landscape", "square"] | None = None
    world_setting: str | None = Field(default=None, max_length=6000)
    style_rules: str | None = Field(default=None, max_length=800)
    negative_prompt: str | None = Field(default=None, max_length=800)
    style_seed: int | None = Field(default=None, ge=0, le=2147483647)
    cover_asset_id: UUID | None = None


class Project(APIModel):
    id: UUID
    title: str
    synopsis: str
    genre: str
    art_style: str
    aspect_ratio: Literal["portrait", "landscape", "square"]
    world_setting: str = ""
    style_rules: str = ""
    negative_prompt: str = ""
    style_seed: int | None = None
    cover_asset_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
    cover_image_url: str | None = None


class ProjectPage(APIModel):
    items: list[Project]
    next_cursor: str | None = None


class EpisodeCreate(APIModel):
    title: str = Field(min_length=1, max_length=120)
    synopsis: str = Field(min_length=1, max_length=10000)
    panel_count: int = Field(default=4, ge=1, le=60)


class EpisodePatch(APIModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    synopsis: str | None = Field(default=None, min_length=1, max_length=10000)
    panel_count: int | None = Field(default=None, ge=1, le=60)
    summary: str | None = Field(default=None, max_length=2000)


class Episode(EpisodeCreate):
    id: UUID
    project_id: UUID
    position: int
    summary: str = ""
    created_at: datetime
    updated_at: datetime


class PlotThreadCreate(APIModel):
    text: str = Field(min_length=1, max_length=500)
    planted_in_episode_id: UUID | None = None
    payoff_in_episode_id: UUID | None = None
    resolved: bool = False


class PlotThreadPatch(APIModel):
    text: str | None = Field(default=None, min_length=1, max_length=500)
    planted_in_episode_id: UUID | None = None
    payoff_in_episode_id: UUID | None = None
    resolved: bool | None = None


class PlotThread(PlotThreadCreate):
    id: UUID
    project_id: UUID
    created_at: datetime
    updated_at: datetime


class ContinuityPreviousSummary(APIModel):
    episode_id: UUID
    position: int
    title: str
    summary: str


class ContinuityOpenThread(APIModel):
    id: UUID
    text: str
    payoff_in_episode_id: UUID | None = None


class ProjectContinuity(APIModel):
    world_setting: str
    previous_summaries: list[ContinuityPreviousSummary]
    open_threads: list[ContinuityOpenThread]


class ProjectPlanRequest(APIModel):
    premise: str = Field(min_length=1, max_length=4000)
    genre: str = Field(min_length=1, max_length=80)
    art_style: str = Field(min_length=1, max_length=240)
    audience: str = Field(default="年轻成人", min_length=1, max_length=40)
    chapter_count: int = Field(default=6, ge=2, le=20)
    aspect_ratio: Literal["portrait", "landscape", "square"] = "portrait"


class PlannedCharacter(APIModel):
    name: str
    role: str
    appearance: str = ""
    hairstyle: str = ""
    outfit: str = ""
    signature_traits: list[str] = Field(default_factory=list)
    personality: str = ""


class PlannedEpisode(APIModel):
    title: str
    synopsis: str


class PlannedThread(APIModel):
    text: str
    planted_in: int | None = None
    payoff_in: int | None = None


class ProjectPlanDraft(APIModel):
    title: str
    premise: str
    genre: str
    art_style: str
    audience: str
    world_setting: str
    characters: list[PlannedCharacter]
    chapters: list[PlannedEpisode]
    threads: list[PlannedThread]
    aspect_ratio: Literal["portrait", "landscape", "square"] = "portrait"


class ProjectFromPlanCreate(ProjectPlanDraft):
    pass


class ProjectFromPlanResult(APIModel):
    project: Project
    episode_ids: list[UUID]


class EpisodeSummaryResult(APIModel):
    episode_id: UUID
    summary: str


class ReaderPanel(APIModel):
    id: UUID
    position: int
    image_url: str | None = None
    dialogue: str = ""
    action: str = ""


class EpisodeReader(APIModel):
    episode: Episode
    panels: list[ReaderPanel]
    previous_episode_id: UUID | None = None
    next_episode_id: UUID | None = None


class CharacterProfile(APIModel):
    generation_source: Literal["ai", "manual"] = "manual"
    role: str = "故事角色"
    appearance: str = ""
    hairstyle: str = ""
    outfit: str = ""
    signature_traits: list[str] = Field(default_factory=list)
    personality: str = ""
    visual_traits: list[str] = Field(default_factory=list)
    image_prompt: str = ""


class CharacterPatch(APIModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    profile: CharacterProfile | None = None
    status: Literal["draft", "in_review", "approved"] | None = None
    reference_locked: bool | None = None


class Character(APIModel):
    id: UUID
    project_id: UUID
    name: str
    profile: CharacterProfile
    reference_asset_id: UUID | None = None
    reference_locked: bool = False
    status: Literal["draft", "in_review", "approved"]
    version: int


class SceneGenerationRequest(APIModel):
    episode_id: UUID | None = None
    guidance: str = Field(default="", max_length=4000)
    scene_ids: list[UUID] = Field(default_factory=list)
    image_only: bool = False
    text_only: bool = False
    cast_mode: Literal["append", "replace"] = "append"

    @model_validator(mode="after")
    def reject_conflicting_modes(self) -> Self:
        if self.image_only and self.text_only:
            raise ValueError("image_only 与 text_only 不能同时为 true")
        return self


class SceneProfile(APIModel):
    description: str = ""
    lighting: str = ""
    palette: str = ""
    visual_traits: list[str] = Field(default_factory=list)


class ScenePatch(APIModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    profile: SceneProfile | None = None
    status: Literal["draft", "in_review", "approved"] | None = None


class Scene(APIModel):
    id: UUID
    project_id: UUID
    name: str
    profile: SceneProfile
    reference_asset_id: UUID | None = None
    status: Literal["draft", "in_review", "approved"]
    version: int


class CharacterGenerationRequest(APIModel):
    story_version_id: UUID | None = None
    guidance: str = Field(default="", max_length=4000)
    character_ids: list[UUID] = Field(default_factory=list)
    image_only: bool = False
    text_only: bool = False
    cast_mode: Literal["append", "replace"] = "append"

    @model_validator(mode="after")
    def reject_conflicting_modes(self) -> Self:
        if self.image_only and self.text_only:
            raise ValueError("image_only 与 text_only 不能同时为 true")
        return self


class StoryboardGenerationRequest(APIModel):
    episode_id: UUID
    panel_count: int = Field(ge=1, le=60)
    pacing: Literal["fast", "balanced", "slow"] = "balanced"
    use_approved_assets: bool = True
    use_continuity: bool = True


class StoryPipelineRequest(APIModel):
    episode_id: UUID
    panel_count: int = Field(ge=1, le=60)
    pacing: Literal["fast", "balanced", "slow"] = "balanced"
    regenerate_characters: bool = True
    character_cast_mode: Literal["append", "replace"] = "append"
    scene_cast_mode: Literal["append", "replace"] = "append"
    use_approved_assets: bool = True
    use_continuity: bool = True


class PanelFields(APIModel):
    scene_description: str = Field(default="", max_length=4000)
    shot: str = Field(default="中景", max_length=240)
    composition: str = Field(default="", max_length=2000)
    character_actions: str = Field(default="", max_length=2000)
    emotion: str = Field(default="", max_length=240)
    dialogue: str = Field(default="", max_length=4000)
    story_purpose: str = Field(default="", max_length=1000)
    image_prompt: str = Field(default="", max_length=8000)
    character_ids: list[UUID] = Field(default_factory=list)
    scene_id: UUID | None = None


class StoryboardPanelCreate(PanelFields):
    id: UUID | None = None


class StoryboardPanelPatch(APIModel):
    position: int | None = Field(default=None, ge=0)
    scene_description: str | None = Field(default=None, max_length=4000)
    shot: str | None = Field(default=None, max_length=240)
    composition: str | None = Field(default=None, max_length=2000)
    character_actions: str | None = Field(default=None, max_length=2000)
    emotion: str | None = Field(default=None, max_length=240)
    dialogue: str | None = Field(default=None, max_length=4000)
    story_purpose: str | None = Field(default=None, max_length=1000)
    image_prompt: str | None = Field(default=None, max_length=8000)
    character_ids: list[UUID] | None = None
    scene_id: UUID | None = None
    review_status: Literal["draft", "in_review", "approved"] | None = None


class StoryboardPanel(PanelFields):
    id: UUID
    episode_id: UUID
    position: int
    review_status: Literal["draft", "in_review", "approved"]
    current_image_asset_id: UUID | None = None
    current_image_url: str | None = None
    version: int
    created_at: datetime
    updated_at: datetime


class PanelOrder(APIModel):
    panel_ids: list[UUID] = Field(min_length=1)


class PanelImageGenerationRequest(APIModel):
    instruction: str = Field(default="", max_length=4000)
    reference_character_ids: list[UUID] = Field(default_factory=list)
    reference_location_ids: list[UUID] = Field(default_factory=list)
    idempotency_key: str | None = Field(default=None, max_length=128)


class PanelImageVersion(APIModel):
    id: UUID
    panel_id: UUID
    asset_id: UUID
    image_url: str
    is_current: bool
    created_at: datetime


class BootstrapLayoutRequest(APIModel):
    default_height_px: int = Field(default=720, ge=80, le=4096)
    default_gap_px: int = Field(default=24, ge=0, le=512)


class SyncLayoutRequest(APIModel):
    follow_current_version: bool = True


class PageOrder(APIModel):
    page_ids: list[UUID] = Field(min_length=1)


class SlotOrder(APIModel):
    slot_ids: list[UUID] = Field(min_length=1)


class PageSlotPatch(APIModel):
    height_px: int | None = Field(default=None, ge=80, le=4096)
    gap_after_px: int | None = Field(default=None, ge=0, le=512)
    image_version_id: UUID | None = None
    follow_current_version: bool | None = None


class PageSlot(APIModel):
    id: UUID
    page_id: UUID
    position: int
    panel_id: UUID
    image_version_id: UUID | None = None
    height_px: int
    gap_after_px: int
    follow_current_version: bool
    created_at: datetime
    updated_at: datetime


class LayoutPage(APIModel):
    id: UUID
    episode_id: UUID
    position: int
    template: Literal["vertical_strip"]
    slots: list[PageSlot]
    created_at: datetime
    updated_at: datetime


class EpisodeLayout(APIModel):
    episode_id: UUID
    template: Literal["vertical_strip"]
    pages: list[LayoutPage]


class LayoutPreviewItem(APIModel):
    slot_id: UUID
    page_id: UUID
    panel_id: UUID
    height_px: int
    gap_after_px: int
    image_url: str | None = None


class LayoutPreview(APIModel):
    episode_id: UUID
    kind: Literal["manuscript_preview"] = "manuscript_preview"
    width_hint_px: int = 720
    items: list[LayoutPreviewItem]


class GenerationTask(APIModel):
    id: UUID
    project_id: UUID | None = None
    episode_id: UUID | None = None
    panel_id: UUID | None = None
    task_type: Literal[
        "character_draft",
        "character_reference_images",
        "scene_draft",
        "scene_reference_images",
        "storyboard_draft",
        "story_pipeline",
        "panel_image",
        "panel_image_edit",
        "export",
    ]
    status: Literal["queued", "running", "succeeded", "failed"]
    progress: int | None = None
    result: dict[str, object] | None = None
    error: dict[str, object] | None = None
    retry_of_task_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class ExportRequest(APIModel):
    format: Literal["png", "png_zip", "production_json"]
    include_unapproved_panels: bool = False


class AnthologyExportRequest(APIModel):
    format: Literal["png_zip", "pdf"]
    episode_ids: list[UUID] = Field(min_length=1, max_length=40)
    include_unapproved_panels: bool = False


class GenerationProviderResumeRequest(APIModel):
    """Explicit resume for failures that may already own a remote provider job."""

    remote_task_id: str | None = Field(default=None, max_length=128)
    job_key: str | None = Field(default=None, max_length=128)
    acknowledge_resubmit: bool = False
