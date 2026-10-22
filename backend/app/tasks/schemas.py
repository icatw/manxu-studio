from pydantic import BaseModel, Field, field_validator


class GeneratedCharacter(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    role: str = Field(min_length=1, max_length=240)
    appearance: str = Field(min_length=1, max_length=2000)
    hairstyle: str = Field(min_length=1, max_length=500)
    outfit: str = Field(min_length=1, max_length=1000)
    signature_traits: list[str] = Field(min_length=1, max_length=8)
    personality: str = Field(min_length=1, max_length=1000)
    reference_image_prompt: str = Field(min_length=1, max_length=3000)


class CharacterGenerationOutput(BaseModel):
    # Empty is valid for cast_mode=append when no new cast members are needed.
    characters: list[GeneratedCharacter] = Field(default_factory=list, max_length=6)


class GeneratedScene(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=2000)
    lighting: str = Field(min_length=1, max_length=500)
    palette: str = Field(min_length=1, max_length=500)
    visual_traits: list[str] = Field(default_factory=list, max_length=8)


class SceneGenerationOutput(BaseModel):
    # Empty is valid for cast_mode=append when no new scenes are needed.
    scenes: list[GeneratedScene] = Field(default_factory=list, max_length=4)


class GeneratedPanel(BaseModel):
    shot: str = Field(min_length=1, max_length=240)
    scene_description: str = Field(min_length=1, max_length=2000)
    composition: str = Field(min_length=1, max_length=1000)
    character_actions: str = Field(min_length=1, max_length=1000)
    emotion: str = Field(min_length=1, max_length=240)
    dialogue: str = Field(default="", max_length=1000)
    story_purpose: str = Field(min_length=1, max_length=1000)
    image_prompt: str = Field(min_length=1, max_length=4000)
    scene_name: str = Field(default="", max_length=120)
    # Names from the project cast that appear in this panel (SB-01 / F04).
    character_names: list[str] = Field(default_factory=list, max_length=8)

    @field_validator("shot", mode="before")
    @classmethod
    def coerce_shot_to_str(cls, value: object) -> object:
        # Some providers return panel index / shot code as a number.
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return str(value)
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return value


class StoryboardGenerationOutput(BaseModel):
    panels: list[GeneratedPanel] = Field(min_length=1, max_length=60)
