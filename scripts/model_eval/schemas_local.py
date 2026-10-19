"""Eval-local plan schema (mirrors serial_service._PlanOutput without DB coupling)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PlannedCharacter(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    role: str = Field(min_length=1, max_length=240)
    appearance: str = Field(min_length=1, max_length=2000)
    hairstyle: str = Field(min_length=1, max_length=500)
    outfit: str = Field(min_length=1, max_length=1000)
    signature_traits: list[str] = Field(min_length=1, max_length=8)
    personality: str = Field(min_length=1, max_length=1000)


class PlannedEpisode(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    synopsis: str = Field(min_length=1, max_length=10000)


class PlannedThread(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    planted_in: int | None = None
    payoff_in: int | None = None


class PlanOutput(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    world_setting: str = Field(min_length=1, max_length=6000)
    characters: list[PlannedCharacter] = Field(min_length=1, max_length=12)
    chapters: list[PlannedEpisode] = Field(min_length=1, max_length=24)
    threads: list[PlannedThread] = Field(default_factory=list, max_length=50)
