from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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


class Project(APIModel):
    id: UUID
    title: str
    synopsis: str
    genre: str
    art_style: str
    aspect_ratio: Literal["portrait", "landscape", "square"]
    created_at: datetime
    updated_at: datetime


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


class Episode(EpisodeCreate):
    id: UUID
    project_id: UUID
    position: int
    created_at: datetime
    updated_at: datetime


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


class Character(APIModel):
    id: UUID
    project_id: UUID
    name: str
    profile: CharacterProfile
    reference_asset_id: UUID | None = None
    status: Literal["draft", "in_review", "approved"]
    version: int


class SceneGenerationRequest(APIModel):
    episode_id: UUID | None = None
    guidance: str = Field(default="", max_length=4000)
    image_only: bool = False


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


class StoryboardGenerationRequest(APIModel):
    episode_id: UUID
    panel_count: int = Field(ge=1, le=60)
    pacing: Literal["fast", "balanced", "slow"] = "balanced"
    use_approved_assets: bool = True


class StoryPipelineRequest(APIModel):
    episode_id: UUID
    panel_count: int = Field(ge=1, le=60)
    pacing: Literal["fast", "balanced", "slow"] = "balanced"
    regenerate_characters: bool = True
    use_approved_assets: bool = True


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


class GenerationTask(APIModel):
    id: UUID
    task_type: Literal[
        "character_draft",
        "scene_draft",
        "scene_reference_images",
        "storyboard_draft",
        "story_pipeline",
        "panel_image",
        "panel_image_edit",
        "export",
    ]
    status: Literal["queued", "running", "succeeded", "failed", "cancelled"]
    progress: int | None = None
    result: dict[str, object] | None = None
    error: dict[str, object] | None = None
    retry_of_task_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class ExportRequest(APIModel):
    format: Literal["png", "production_json"]
    include_unapproved_panels: bool = False


class GenerationProviderResumeRequest(APIModel):
    """Explicit resume for failures that may already own a remote provider job."""

    remote_task_id: str | None = Field(default=None, max_length=128)
    job_key: str | None = Field(default=None, max_length=128)
    acknowledge_resubmit: bool = False
